# A History of the World, According to War
Tools for building and producing the podcast A History of the World, According to War

## transcribe_podcast.py
This tool takes an episode of a two-person podcast and generates a transcription. It does this using two services. First, it uploads the audio to IBM Watson. This returns a (reasonably) accurate transcription with the timings and different speakers identified. Then, it uploads the audio to OpenAI's Whisper service. I prefer the accuracy of this service over Watson's, but it doesn't handle speaker identification. Finally, it takes the timestamps from these two transcriptions and merges the speaker identification from Watson with the text from OpenAI, and formats in a human-readable format.
