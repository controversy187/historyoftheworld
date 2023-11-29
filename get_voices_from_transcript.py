import csv
import requests
import json
import local_config

def api_call(field1, field3):
    url = 'https://api.elevenlabs.io/v1/text-to-speech/' + local_config.PODCASTER_ID  # replace with your API endpoint
    headers = {
        "accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": local_config.XI_API_KEY
    }
    data = {
        "text": field3
    }
    print(data)
    response = requests.post(url, headers=headers, data=json.dumps(data))  # convert dict to JSON
    return response

with open('script.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        if row[2]:  # Check if there is data in the third field (index 2)
            api_response = api_call(row[0], row[2])  # Call API with data from first and third fields
            if api_response.status_code == 200:  # Check if the request was successful
                filename = f"{row[0]}-Victor.mp3"  # Create filename from 1st and 3rd fields
                with open(filename, 'wb') as mp3_file:
                    print("Writing " + filename + "...")
                    mp3_file.write(api_response.content)  # Write the content of the response to a file
                print(f"File saved as {filename}")
            else:
                print(f"Request failed with status code {api_response.status_code}")