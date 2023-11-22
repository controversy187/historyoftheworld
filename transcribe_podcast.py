import local_config  # Importing your local_config file for API keys and endpoints
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from openai import OpenAI

client = OpenAI(api_key=local_config.OPENAI_API_KEY)
import json
import os
from openai import OpenAI

# Function to save transcription to a file
def save_transcript(filename, transcript):
    # Check if the transcript is a dictionary and convert it to a string
    if isinstance(transcript, dict):
        transcript = json.dumps(transcript, indent=2)
    
    with open(filename, 'w') as file:
        file.write(transcript)

# Function to transcribe using IBM Watson
def transcribe_with_watson(file_path):
    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    saved_transcript_path = f"{base_filename}_watson_transcript.json"

    # Check if the transcript already exists
    if os.path.exists(saved_transcript_path):
        with open(saved_transcript_path, 'r') as file:
            return json.load(file)

    # Setup for Watson transcription
    authenticator = IAMAuthenticator(local_config.WATSON_API_KEY)
    speech_to_text = SpeechToTextV1(authenticator=authenticator)
    speech_to_text.set_service_url(local_config.WATSON_SERVICE_URL)

    with open(file_path, 'rb') as audio_file:
        watson_result = speech_to_text.recognize(
            audio=audio_file,
            content_type='audio/mp3',
            model='en-US_BroadbandModel',
            timestamps=True,
            speaker_labels=True
        ).get_result()

    # Save the transcript
    with open(saved_transcript_path, 'w') as file:
        json.dump(watson_result, file, indent=2)

    return watson_result

# Function to transcribe using OpenAI's Whisper API
def transcribe_with_whisper_api(file_path):
    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    saved_transcript_path = f"{base_filename}_whisper_transcript.json"

    # Check if the transcript already exists
    if os.path.exists(saved_transcript_path):
        with open(saved_transcript_path, 'r') as file:
            return file.read()

    # Setup for OpenAI transcription
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json"
        )
        json_response = response.model_dump_json()
        with open(saved_transcript_path, 'w') as file:
            file.write(json_response)

    return response.model_dump_json()

# Function to merge transcripts and apply speaker labels
def merge_transcripts(processed_speaker_json, whisper_transcript):
    # Parse the processed speaker JSON
    speaker_data = json.loads(processed_speaker_json)
    # Ensure whisper_transcript is a dictionary
    whisper_transcript = json.loads(whisper_transcript)
    merged_data = []

    # Iterate through the speaker data
    for speaker_entry in speaker_data:
        start_time = speaker_entry['start_time']
        speaker_text = ""

        # Find corresponding text in the Whisper transcript
        for segment in whisper_transcript['segments']:
            if start_time >= segment['start'] and start_time <= segment['end']:
                speaker_text = segment['text']
                break

        # Add the combined data to the merged data list
        merged_entry = {
            'speaker': speaker_entry['speaker'],
            'start_time': start_time,
            'text': speaker_text
        }
        merged_data.append(merged_entry)

    # Return the merged data as JSON
    return json.dumps(merged_data, indent=2)

def process_watson_transcript_to_json(watson_transcript):
    speaker_data = []

    # Iterate through each speaker label in the Watson transcript
    for label in watson_transcript['speaker_labels']:
        speaker_entry = {
            'speaker': label['speaker'],
            'start_time': label['from']
        }
        # Add the speaker entry to the list if it's a new speaker or a new segment of speech
        if not speaker_data or (speaker_data[-1]['speaker'] != speaker_entry['speaker'] or
                                speaker_data[-1]['start_time'] != speaker_entry['start_time']):
            speaker_data.append(speaker_entry)

    # Return the processed data as JSON
    return json.dumps(speaker_data, indent=2)

def consolidate_transcript(merged_transcript):
    consolidated_data = []
    current_speaker = None
    current_text = ""
    last_end_time = None

    for entry in merged_transcript:
        # Start a new entry when the speaker changes or there's a gap in the timestamps
        if entry['speaker'] != current_speaker:
            if current_speaker is not None and current_text != entry['text']:
                consolidated_data.append({
                    'speaker': current_speaker,
                    'text': current_text.strip()
                })
            current_speaker = entry['speaker']
            current_text = entry['text']
        else:
            # Avoid repeating the text if it's already included
            if not current_text.endswith(entry['text'].strip()):
                current_text += " " + entry['text']

        last_end_time = entry['start_time']  # Assuming end time is not available

    # Add the last entry
    consolidated_data.append({
        'speaker': current_speaker,
        'text': current_text.strip()
    })

    return consolidated_data


def create_readable_transcript(consolidated_transcript):
    readable_transcript = ""
    speaker_names = {0: "Brett", 1: "Victor"}
    last_speaker = None
    
    for entry in consolidated_transcript:
        speaker_name = speaker_names.get(entry['speaker'], f"Speaker {entry['speaker']}")
        readable_transcript += f"{speaker_name}: {entry['text']}\n"

    return readable_transcript

def refine_transcript_with_openai(transcript, api_key):
    prompt = "Please analyze this transcript for speaker attribution errors and refine it. Do not change the text itself, only which speaker you believe said it, based on the context of the conversation. If you are unsure about a particular line, denote that line with a triple asterisk ***\n\n" + transcript

    
    response = client.chat.completions.create(
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="gpt-4-1106-preview",
        max_tokens=2048,  # Adjust based on your needs
        temperature=0
    )

    refined_transcript = response.choices[0].message.content.strip()
    return refined_transcript

# Main method to handle the transcription process
def process_transcription(file_path):
    base_filename = os.path.splitext(os.path.basename(file_path))[0]

    # Transcribe using both services
    print("Using IBM's Watson to trascribe audio and identify speakers...")
    watson_transcript = transcribe_with_watson(file_path)
    processed_speaker_json = process_watson_transcript_to_json(watson_transcript)
    save_transcript(f"{base_filename}_watson_speakers.json", processed_speaker_json)

    print("Using OpenAI's Whisper to trascribe audio more accurately...")
    whisper_transcript = transcribe_with_whisper_api(file_path)

    # Merge the transcripts
    print("Merging transcripts...")
    merged_transcript_json = merge_transcripts(processed_speaker_json, whisper_transcript)
    save_transcript(f"{base_filename}_merged_transcript.json", merged_transcript_json)

    # Process the transcript
    print("Making transcripts human-readable...")
    consolidated_transcript = consolidate_transcript(json.loads(merged_transcript_json))
    readable_transcript = create_readable_transcript(consolidated_transcript)
    # Specify the filename for the readable transcript
    readable_transcript_filename = f"{base_filename}_readable_transcript.txt"
    save_transcript(readable_transcript_filename, readable_transcript)

    # Send the transcript to OpenAI for speaker attribution error analysis and correction.
    print("Sending transcript to OpenAI to identify and correct speaker attribution...")
    refined_transcript = refine_transcript_with_openai(readable_transcript, local_config.OPENAI_API_KEY)
    refined_transcript_filename = f"{base_filename}_refined_transcript.txt"
    save_transcript(refined_transcript_filename, refined_transcript)

    # Display the first few lines of the readable transcript for review
    print(f"Transcriptions saved for {base_filename}")
    print("Done!")




# Path to the audio file
audio_file_path = 'mp3s/Episode 01 - The Battle of Megiddo.mp3'

# Process the transcription
process_transcription(audio_file_path)

