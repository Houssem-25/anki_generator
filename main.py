from deep_translator import GoogleTranslator
from pattern.de import parse
from pattern.de import conjugate
from german_nouns.lookup import Nouns
import pickle 
from gtts import gTTS
import shutil
import os
from tqdm import tqdm


nouns = Nouns()
gender_to_article = {"m" : '<span style="color: rgb(10, 2, 255)">Der</span> ',
                     "f" : '<span style="color: rgb(170, 0, 0)"> Die</span> ',
                     "n" : '<span style="color: rgb(0, 255, 51)">Das</span> ',
                     "p" : '<span style="color: rgb(170, 0, 0)"> Die</span> ',
                     "pl": '<span style="color: rgb(170, 0, 0)"> Die</span> '}

german_to_eng, german_to_eng_ids, new_english_texts = [], [], []

with open('german_to_eng.pickle', 'rb') as handle:
    german_to_eng = pickle.load(handle)

with open('german_to_eng_ids.pickle', 'rb') as handle:
    german_to_eng_ids = pickle.load(handle)

with open('new_english_texts.pickle', 'rb') as handle:
    new_english_texts = pickle.load(handle)


def warmup_parser():
    nbr_attempt = 0
    while(nbr_attempt<10):
        try:
            parse("test")
            break
        except:
            nbr_attempt +=1
            continue
    print(f"Parser warmed_up after {nbr_attempt}")
    nbr_attempt = 0
    while(nbr_attempt<10):
        try:
            conjugate("test")
            break
        except:
            nbr_attempt +=1
            continue
    print(f"Parser warmed_up after {nbr_attempt}")



def translate_to_english(german_word):
    english_translation = GoogleTranslator(source='german', target='english').translate(german_word)
    return english_translation

def get_german_example(german_word):
    for de_sentence, eng_translation in german_to_eng:
        if  len(de_sentence.split(" ")) < 10 and german_word.lower() in de_sentence.lower() :
            return "<br> " + de_sentence ,  "<br> " + eng_translation
    return "",""

def translate_with_examples(file_path):
    with open(file_path, 'r', encoding='utf-8') as file, open('anki/anki.txt', 'w', encoding='utf-8') as anki_file:
        for line in tqdm(file, desc="Processing lines", unit=" lines"):
            line = line.strip() # Remove leading/trailing whitespace
            if not line: # Check if the line is empty after stripping
                continue # Skip to the next line

            german_word = line.split(";")[0]
            audio_word = generate_audio(german_word)
            english_translation = translate_to_english(german_word)
            german_word = german_word.lower()
            german_word = german_word.replace("der ","").replace("die ", "").replace("das ","").replace(" ", "")
            word_type = get_german_word_type(german_word)
            german_word_spaced = " "+german_word+ " "
            if len(line.strip().split(";"))>1:
                de_sentence , eng_translation = "<br> " + line.strip().split(";")[1],  "<br> " +   line.strip().split(";")[2]
            else:
                de_sentence , eng_translation = get_german_example(german_word_spaced)
            plural = ""
            german_word = line.strip().split(";")[0].replace("die ", "").replace("das ","")
            if word_type =="noun":
                german_word, plural = get_plural(german_word)
            output_line = f"{english_translation} {eng_translation};  {german_word} {plural} {audio_word} {de_sentence};"
            anki_file.write(output_line)
            anki_file.write('\n')

def get_german_word_type(german_word):
    parsed = parse(german_word)
    if parsed is not None and len(parsed) > 0:
        pos_tag = parsed.split("/")[1]
        if pos_tag.startswith("V"):
            return "verb"
        elif pos_tag.startswith("JJ"):
            return "adjectif"
        elif len(nouns[german_word]) > 0:
            return "noun"
    return "unknown"

def get_plural(german_word):
    plural = ""
    article = ""
    if "nominativ plural" in nouns[german_word][0]["flexion"].keys():
        plural  = "<br> " + gender_to_article["pl"]  +  nouns[german_word][0]["flexion"]["nominativ plural"]
    elif "nominativ plural 2" in nouns[german_word][0]["flexion"].keys():
        plural =  "<br> " + gender_to_article["pl"]  + nouns[german_word][0]["flexion"]["nominativ plural 2"]
    if "genus" in nouns[german_word][0].keys():
        article = gender_to_article[nouns[german_word][0]["genus"]] 
    elif "genus 1" in nouns[german_word][0].keys() and "genus 2" in nouns[german_word][0].keys():
        article = gender_to_article[nouns[german_word][0]["genus 1"]]  + gender_to_article[nouns[german_word][0]["genus 2"]] 
    return article  + german_word.capitalize(),  plural

def generate_audio(text):
    output_file = os.path.join("anki",text.replace(" ","_")+".mp3")
    try:
        # Create a gTTS object
        tts = gTTS(text=text, lang='de')
        # Save the speech to a file
        tts.save(output_file)
        out = text.replace(" ","_")
        copy_to_anki_media(output_file)
        return f"[sound:{out}.mp3]"
    except Exception as e:
        return ""



def copy_to_anki_media(file_path):
    # Define the destination directory
    anki_media_dir = os.path.join(os.getenv('APPDATA'), 'Anki2', 'Houssem', 'collection.media')

    # Ensure the destination directory exists
    os.makedirs(anki_media_dir, exist_ok=True)

    try:
        # Copy the file to the Anki media directory
        shutil.copy2(file_path, anki_media_dir)
        print(f"File '{os.path.basename(file_path)}' copied successfully to Anki media directory.")
    except FileNotFoundError:
        print("Error: File not found.")
    except PermissionError:
        print("Error: Permission denied.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    warmup_parser()
    file_path = "new_words.txt"  # Change this to your file path
    translate_with_examples(file_path)