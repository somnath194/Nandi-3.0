import asyncio
import websockets
import whisperx
import pyaudio
import base64
import wave
from text_correction_v5 import *  # noqa: F403
import re
import os
import json
import torch
import numpy as np
from spellchecker import SpellChecker
from silero_vad import load_silero_vad, get_speech_timestamps
import io

vad_model = load_silero_vad()

MAX_BUFFER_DURATION = 10  # seconds - prevent buffer overflow

spell = SpellChecker() 
spell.word_frequency.load_text_file('correctionDict.txt')

# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
BATCH_SIZE = 6
WHISPER_MAX_LENGTH_AUDIO = 25

# Initialize multiple Whisper models
model = whisperx.load_model('deepdml/faster-whisper-large-v3-turbo-ct2', device='cuda', compute_type='float16', language='en')

# model = whisperx.load_model('medium', device='cuda', compute_type='float16', language='en')

audio = pyaudio.PyAudio()

client_map = {}

# Silence detection parameters
SILENCE_THRESHOLD = 0.2
MIN_SILENCE_LENGTH = 0.5  # seconds
MIN_AUDIO_DURATION = 2

# Define parameters
samples_to_remove = 44  # Number of samples to remove from the beginning of each chunk
sample_width = 2  # Number of bytes per sample (2 bytes for 16-bit audio)
bytes_to_remove = samples_to_remove * sample_width


# Function to check and correct spelling
def spell_check(text):
    corrected_text = []
    words = text.split()

    for word in words:
        # Check if the word is misspelled
        if word in spell.unknown([word]):  # If word is not recognized
            # Get the most likely correction
            correction = spell.correction(word)
            corrected_text.append(correction if correction else word)
        else:
            corrected_text.append(word)
    
    return " ".join(corrected_text)


# Function to convert audio bytes to numpy array for WhisperX
def audio_bytes_to_array(audio_bytes, channels=CHANNELS, sample_width=2, sample_rate=RATE):
    """Convert raw audio bytes to numpy array that WhisperX can process"""
    # Convert bytes to NumPy array
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    
    # Normalize to -1.0 to 1.0 range
    audio_np = audio_np / 32768.0
    
    return audio_np


async def receive_and_write_audio():
    while True:
        try:
            # async with websockets.connect('wss://demo.ezheal.in/sttsocket') as websocket:
            async with websockets.connect('ws://localhost:8100') as websocket:
                print("Connected to Node.js WebSocket server")
                try:
                    while True:
                        # Handshake
                        await websocket.send(json.dumps({"clientType": "python"}))

                        # Receiving Audio
                        audio_data_base64 = await websocket.recv()
                        data = json.loads(audio_data_base64)

                        clientId = data["clientId"]
                        audio_base64 = data["base64Audio"]
                        
                        # Decode base64
                        audio_data = base64.b64decode(audio_base64)

                        # Remove the initial bytes to avoid spikes
                        cleaned_audio_data = audio_data[bytes_to_remove:]

                        if clientId not in client_map:
                            client_map[clientId] = b''

                        client_map[clientId] += cleaned_audio_data
                        
                        # Limit buffer size to prevent overflow - ADD THIS HERE
                        buffer_duration = len(client_map[clientId]) / RATE / 2
                        if buffer_duration > MAX_BUFFER_DURATION:
                            max_samples = int(MAX_BUFFER_DURATION * RATE * 2)
                            client_map[clientId] = client_map[clientId][-max_samples:]
                            # print(f"Buffer overflow prevented for client {clientId}")

                        # Check for silence
                        audio_array = np.frombuffer(client_map[clientId], dtype=np.int16).astype(np.float32) / 32768.0
                        speech_timestamps = get_speech_timestamps(audio_array, vad_model, sampling_rate=RATE) # type: ignore
                        
                        if speech_timestamps:
                            last_speech_end = speech_timestamps[-1]['end'] / RATE
                            buffer_duration = len(client_map[clientId]) / RATE / 2  # divide by 2 because it's 16-bit audio
                            silence_duration = buffer_duration - last_speech_end

                            # print("silence duration: ", silence_duration)

                            if buffer_duration < MIN_AUDIO_DURATION:
                                status = "unconfirmed"
                            elif buffer_duration > WHISPER_MAX_LENGTH_AUDIO:
                                status = "confirmed"
                            else:
                                status = "confirmed" if silence_duration >= MIN_SILENCE_LENGTH else "unconfirmed"

                            # Schedule the transcribing coroutine - pass audio bytes directly
                            asyncio.create_task(transcribe_and_send(websocket, client_map[clientId], clientId, status, silence_duration))

                            if status == "confirmed":
                                client_map[clientId] = b''

                except websockets.exceptions.ConnectionClosed:
                    print("\n \t Server Disconnected.")

        except Exception as e:
            print(f"Connection failed: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

async def transcribe_and_send(websocket, audio_bytes, clientId, status, silence_duration):
    try:
        await asyncio.sleep(0.2)
        
        # Convert audio bytes to numpy array that WhisperX can process
        audio_array = audio_bytes_to_array(audio_bytes)
        
        # Process with WhisperX directly from memory
        result = model.transcribe(audio_array, batch_size=BATCH_SIZE)

        text_ = None
        # Process transcription result
        if 'segments' in result and result['segments']:
            transcript = result['segments'][0]['text'] 

            # Post processing Transcript        
            text_ = transcript.strip()
            # text_before = text_
            # text_after = re.sub(r'\b(\w+)\.(?=\s|$)', r'\1', text_before)
            # text_lower = text_after.lower()
            # text_lower = spell_check(text_lower)
            
            # text_ = convert_measurement(text_lower)
            
            data = {
                "status": status,
                "clientType": "python",
                "clientId": clientId,
                "transcription": text_
            }

            json_string = json.dumps(data)

            # Send transcription back to the Client
            await websocket.send(json_string)

        # print("silence duration: ", silence_duration)
        # print("status: ", status)
        # print("transcription: ", text_)
        # print("\n")

        # Remove client from map if status is confirmed
        if status == "confirmed" and clientId in client_map:
            del client_map[clientId]

    except Exception as e:
        print(f"Error in transcription: {e}")
        await websocket.send('Error in transcription')

    finally:
        # print("Clear cuda cache")
        torch.cuda.empty_cache()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(receive_and_write_audio())
    except KeyboardInterrupt:
        print("\n \t SERVER STOPPED.")
    finally:
        # Clean up resources
        audio.terminate()
