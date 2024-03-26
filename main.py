import json
import re
import argparse
import pretty_midi
from json_repair import repair_json



# Function to load a JSON file
def load_json_file(file_path):
    with open(file_path, "r") as file:
        json_string = file.read()
        return json.loads(repair_json(json_string))


# Function to decode a single key using the parameters data
def decode_key(key, parameters_data):
    # Extract the parameter ID from the key
    match = re.match(r"(\d+)_(\d+)", key)
    if match:
        param_id = int(match.group(2))

        # Find the corresponding parameter in the parameters data
        for param in parameters_data["fields"]:
            if param["paramId"] == param_id:
                if "comment" in param:
                    return f'{param["name"]} ({param["comment"]})'
                else:
                    return param["name"]
    return "Unknown parameter"


# Main function to decode the project file
def decode_project_file(project_file_path, parameters_file_path):
    # Load the project and parameters files
    project_data = load_json_file(project_file_path)
    parameters_data = load_json_file(parameters_file_path)

    decoded_project = {
        "device": {},
        "project": {},
        "state": {},
        "control": {},
        "track1": {},
        "track2": {},
        "track3": {},
        "track4": {},
    }
    
    tempo_lsb = None
    tempo_mdsb = None
    tempo_msb = None
    tempo = None

    # Iterate over each item in the project file
    for key, value in project_data.items():
        
        sections = key.split("_")
        track_id = sections[0]

        track = {
            "version": "device",
            "device": "device",
            "120": "project",
            "121": "state",
            "122": "control",
            "123": "track1",
            "124": "track2",
            "125": "track3",
            "126": "track4",
        }.get(track_id, "unknown")

        # Handle device and unknown tracks
        if track == "device":
            decoded_project["device"][key] = value
            continue
        if track == "project" and tempo is None:
            # Decode Tempo
            if key == "120_70":
                # Project tempo part 3 (LSB)
                tempo_lsb = bin(value)
            elif key == "120_71":
                # Project tempo part 2 (MidSB)
                tempo_mdsb = bin(value)
            elif key == "120_72":
                # Project tempo part 1 (MSB)
                tempo_msb = bin(value)
                
            if tempo_msb is not None and tempo_mdsb is not None and tempo_lsb is not None:
                tempo = tempo_msb + tempo_mdsb.replace("0b", "") + tempo_lsb.replace("0b", "")
                tempo = float(int(tempo, 2) / 100)   
                decoded_project[track]['tempo'] = tempo
                print(f"Detected Tempo: {tempo}")
                continue
            
        elif track == "unknown":
            continue

        decoded_key = decode_key(key, parameters_data)

        pattern_id = "0"
        multiplier = "0"
        note_id = "0"

        # Break sections into variables
        if len(sections) == 2:
            param_id = sections[1]
        elif len(sections) == 3:
            param_id, pattern_id = sections[1:]
        elif len(sections) == 4:
            param_id, pattern_id, multiplier = sections[1:]
        if len(sections) == 5:
            param_id, pattern_id, multiplier, note_id = sections[1:]

        # Parse the param_id, there always should be one
        if param_id not in decoded_project[track]:
            decoded_project[track][param_id] = {}

        if pattern_id not in decoded_project[track][param_id]:
            decoded_project[track][param_id][pattern_id] = {}
        if multiplier not in decoded_project[track][param_id][pattern_id]:
            decoded_project[track][param_id][pattern_id][multiplier] = {}
        if note_id not in decoded_project[track][param_id][pattern_id][multiplier]:
            decoded_project[track][param_id][pattern_id][multiplier][note_id] = {}

        decoded_project[track][param_id][pattern_id][multiplier][note_id] = value

    return decoded_project


def to_midi_track(midi_data, decoded_track, track, is_drum):

    bpm = decoded_track['project']['tempo']
    decoded_track = decoded_track[track]

    if is_drum:
        steps = decoded_track["54"]
        pitches = decoded_track["117"]
        gates = decoded_track["118"]
        velocities = decoded_track["119"]
    else:
        steps = decoded_track["50"]
        pitches = decoded_track["109"]
        gates = decoded_track["110"]
        velocities = decoded_track["111"]

    track_steps = {}

    # Calculate the steps with actual notes on them in the pattern
    for pattern, data in steps.items():
        pattern_note_steps = {}

        for mult, subdata in data.items():
            # Still need to figure out what the mult data is for, could be undo states
            if mult == "1":

                for note, step in subdata.items():
                    if step != 127:
                        if int(step) not in pattern_note_steps:
                            pattern_note_steps[int(step)] = {}

                        pattern_note_steps[int(step)][note] = {
                            "pitch": int(pitches[pattern][mult][note]),
                            "velocity": int(velocities[pattern][mult][note]),
                            "gate": int(gates[pattern][mult][note]),
                        }

        track_steps[int(pattern)] = pattern_note_steps

    track_data = dict(sorted(track_steps.items()))

    # Create an Instrument instance (using a piano here, but you can choose any)
    if is_drum:
        instrument = pretty_midi.Instrument(is_drum=is_drum, program=0)
    else:
        instrument = pretty_midi.Instrument(
            program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano")
        )

    # Define the duration of a 1/16th note in seconds (assuming 120 BPM for simplicity)
    # Use parameters from the file to figure out tempo later
    sixteenth_note_duration = 60 / (bpm * 4)
    pattern_cursor = 0
    
    # Process each note in the dictionary
    for pattern, step_info in track_data.items():
        for step, note_info in step_info.items():
            for note_id, attrs in note_info.items():
                # Calculate the start time for the note (step * duration of a sixteenth note)
                start_time = step * sixteenth_note_duration * 2 + pattern_cursor * sixteenth_note_duration * 2

                # Calculate the end time based on the gate value (assuming gate values are in sixteenth note durations)
                end_time = start_time + attrs["gate"] / 2 * sixteenth_note_duration

                # Create a new Note object for this note
                note = pretty_midi.Note(
                    velocity=attrs["velocity"],
                    pitch=attrs["pitch"],
                    start=start_time,
                    end=end_time,
                )

                # Add the note to the instrument
                instrument.notes.append(note)
        pattern_cursor = pattern_cursor + 64
                
    # Add the instrument to the PrettyMIDI object
    midi_data.instruments.append(instrument)
    return midi_data


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", "-i", type=str, default="KeyStepPro")
    parser.add_argument("--project", "-p", type=str, default="Sample")
    parser.add_argument("--midi", "-m", type=str, default="Sample.mid")
    parser.add_argument("--json", "-j", type=str)
    args = parser.parse_args()

    # Paths to your project and parameters (preferences) files
    project_file_path = f"Projects/{args.project}.{args.instrument}"
    parameters_file_path = f"Instruments/{args.instrument}.json"

    # Decode the project file
    decoded_project_data = decode_project_file(project_file_path, parameters_file_path)

    # Initialize PrettyMIDI object
    midi_data = pretty_midi.PrettyMIDI()
    for i in range(1, 5):
        if i == 1:
            is_drum = True
        else:
            is_drum = False
        midi_data = to_midi_track(midi_data, decoded_project_data, f"track{i}", is_drum)

    # Write out the MIDI data to a new file
    midi_data.write(args.midi)
    print(f"MIDI written to {args.midi}")
    
    # Output or process the decoded project data for debugs
    if args.json:
        json_out = json.dumps(decoded_project_data, indent=4, sort_keys=True)
        with open("output.json", "w") as fp:
            fp.write(json_out)
