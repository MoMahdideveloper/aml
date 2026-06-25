
import os
import sys
import subprocess
import polib
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
KIE_API_KEY = os.getenv("KIE_API_KEY")
KIE_BASE_URL = "https://api.kie.ai/api/v1/"
SOURCE_LANG = "en"
TARGET_LANG = "fa"
TRANSLATIONS_DIR = "translations"

if not KIE_API_KEY:
    print("Error: KIE_API_KEY environment variable is not set.")
    sys.exit(1)

# Initialize OpenAI client for Kie.ai
client = OpenAI(
    api_key=KIE_API_KEY,
    base_url=KIE_BASE_URL
)

def run_command(command):
    """Run a shell command and check for errors."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        print(result.stderr)
        return False
    return True

def extract_and_update():
    """Extract strings and update .po files."""
    print("--- 1. Extracting messages ---")
    if not run_command(f"{sys.executable} -m babel.messages.frontend extract -F babel.cfg -k _l -o messages.pot ."):
        return False

    print(f"--- 2. Initialize/Update {TARGET_LANG} catalog ---")
    po_file = os.path.join(TRANSLATIONS_DIR, TARGET_LANG, "LC_MESSAGES", "messages.po")
    
    if not os.path.exists(po_file):
        if not run_command(f"{sys.executable} -m babel.messages.frontend init -i messages.pot -d {TRANSLATIONS_DIR} -l {TARGET_LANG}"):
            return False
    else:
        if not run_command(f"{sys.executable} -m babel.messages.frontend update -i messages.pot -d {TRANSLATIONS_DIR}"):
            return False
    return True

def translate_with_ai():
    """Find untranslated strings and translate them using Kie.ai."""
    print(f"--- 3. Translating to {TARGET_LANG} using Kie.ai ---")
    po_file_path = os.path.join(TRANSLATIONS_DIR, TARGET_LANG, "LC_MESSAGES", "messages.po")
    
    if not os.path.exists(po_file_path):
        print(f"Error: {po_file_path} not found.")
        return False

    po = polib.pofile(po_file_path)
    untranslated = [entry for entry in po if not entry.msgstr and entry.msgid]
    
    if not untranslated:
        print("No untranslated strings found.")
        return True

    print(f"Found {len(untranslated)} untranslated strings.")

    # Batch process or simple loop (using loop for simplicity and error handling)
    for i, entry in enumerate(untranslated):
        print(f"Translating ({i+1}/{len(untranslated)}): {entry.msgid}")
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o", # Using standard model name as it's OpenAI compatible
                messages=[
                    {"role": "system", "content": f"You are a professional translator. Translate the following English text to {TARGET_LANG} (Persian/Farsi). Return ONLY the translation, no explanations. Preserve any format specifiers like %(name)s or {{value}}."},
                    {"role": "user", "content": entry.msgid}
                ],
                temperature=0.3
            )
            
            translation = response.choices[0].message.content.strip()
            # Remove keys if AI adds them by mistake (rare but possible)
            translation = translation.replace('"', '').replace("'", "") 
            
            entry.msgstr = translation
            print(f" -> {translation}")
            
        except Exception as e:
            print(f"Failed to translate '{entry.msgid}': {e}")

    po.save()
    print("Translations saved.")
    return True

def compile_translations():
    """Compile .po to .mo."""
    print("--- 4. Compiling translations ---")
    return run_command(f"{sys.executable} -m babel.messages.frontend compile -d {TRANSLATIONS_DIR}")

def main():
    if not extract_and_update():
        sys.exit(1)
    
    if not translate_with_ai():
        sys.exit(1)
        
    if not compile_translations():
        sys.exit(1)
        
    print("--- Done! ---")

if __name__ == "__main__":
    main()
