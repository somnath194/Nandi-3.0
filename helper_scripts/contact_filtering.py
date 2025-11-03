
import json
import re
# convert VCF files to a dictionary format
def contacts_to_dict(vcf_path):
    contacts = {}
    name, phone = None, None
    
    with open(vcf_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            # Name
            if line.startswith("FN:") or line.startswith("FN;"):
                name = line.split(":", 1)[1].strip()
                # Clean up emojis/special symbols from names
                name = re.sub(r'[^\w\s]', '', name).strip().lower()
            
            # Phone
            elif line.startswith("TEL"):
                phone = line.split(":", 1)[1].strip()
                # Normalize phone number
                phone = phone.replace(" ", "").replace("-", "")
            
            # End of a contact
            elif line == "END:VCARD":
                if name and phone:
                    contacts[name] = phone
                name, phone = None, None

    return contacts



# 10 digit Number extraction and filtering
def is_company_number(number):
    # Ignore numbers with non-digit characters or less than 10 digits
    # You can add more rules here if needed
    return not re.fullmatch(r'\+?\d{10,}', number)

def extract_last_10_digits(number):
    digits = re.sub(r'\D', '', number)  # Remove non-digit characters
    if len(digits) >= 10:
        return digits[-10:]
    return None

# with open('contacts.json', 'r', encoding='utf-8') as f:
#     contacts = json.load(f)

contacts = contacts_to_dict('Contacts.vcf')

filtered_contacts = {}
for name, number in contacts.items():
    if is_company_number(number):
        continue
    last_10 = extract_last_10_digits(number)
    if last_10:
        filtered_contacts[name] = last_10

# Save to a new JSON file
with open('contacts_10digit.json', 'w', encoding='utf-8') as f:
    json.dump(filtered_contacts, f, indent=4)

print("Saved filtered contacts to contacts_10digit.json")
