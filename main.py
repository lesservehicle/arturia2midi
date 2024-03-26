import json
import re
import argparse
import pretty_midi
from json_repair import repair_json



# Function to load a JSON file
def load_json_file(file_path):
    with open(file_path, "r") as file:
        json_string = file.read()
        
        # Using repair_json library here because the default output from Arturia is 
        # an incorrectly formatted JSON file
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
    swing = None

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
        
        """ 
            Decoding Tempo
            
            Tempo is determined by combining three fields for least-significant bits (LSB), middle significance bits (MidSB)
            and most significant bits (MSB). For example, a tempo of 120.00 is represented in the three fields as follows:
            
                  Key: Value                    Binary
                - 120_70: 96    (MSB)       ->  1100000
                - 120_71: 93    (MidSB)     ->  1011101
                - 120_72: 0     (LSB)       ->  0000000
                
                Combined binary             ->  110000010111010000000
                In decimal                  ->  12000
                / 100 for Tempo             ->  120.00
        """
        
        if track == "project" and tempo is None:
            
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
          
        # Find swing parameter  
        if track == "project" and swing is None:
            if key == "120_74":
                swing = value
                decoded_project[track]['swing'] = swing
                continue        
        
        """
        Determine if Track 1 is in SEQ or DRUM mode:

        This parameter is set per pattern, but a limitation in MIDI allows us to only set one instrument type per track.
        Therefore, we'll derive the mode from the first pattern in the track.

        The value for SEQ/DRUM mode is derived from the first bit in the value of Parameter ID 100. For example, for 
        Track 1 (123), Pattern 1 (1):
                Key: Value              Binary
            -   123_100_1: 26       ->  00011010
            -   
        """
        
        if track == "track1":
            if key == "123_100_1":
                
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

        decoded_project[track][param_id][pattern_id][multiplier][note_id]['value'] = value
        decoded_project[track][param_id][pattern_id][multiplier][note_id]['key'] = key
        decoded_project[track][param_id][pattern_id][multiplier][note_id]['decoded_key'] = decoded_key

    return decoded_project


def to_midi_track(midi_data, decoded_track, track, is_drum):

    # Grab the Project's tempo parameter that we derived earlier
    bpm = decoded_track['project']['tempo']
    
    # Copy just the information for a specific track
    decoded_track = decoded_track[track]

    # It's important to determine if Track 1 is DRUM or SEQ, because the Parameter IDs
    # that we need to fetch are going to be different based on that.

    if is_drum:
        # Parameter ID 54:  DRUM step corresponding step
        steps = decoded_track["54"]
        # Parameter ID 117: DRUM note pitch
        pitches = decoded_track["117"]
        # Parameter ID 118: DRUM note gate length 
        gates = decoded_track["118"]
        # Parameter ID 119: DRUM note velocity
        velocities = decoded_track["119"]
    else:
        # Parameter ID 50:  Seq note corresponding step
        steps = decoded_track["50"]
        # Parameter ID 109: Seq note pitch
        pitches = decoded_track["109"]
        # Parameter ID 110: Seq note gate length
        gates = decoded_track["110"]
        # Parameter ID 111: Seq note velocity
        velocities = decoded_track["111"]

    # We have to derive the active steps from Parameter ID 54 or 50 before we can iterate on them
    # and fill them in with pitch, gate, and velocity
    track_steps = {}

    # Calculate the steps with actual notes on them in the pattern
    for pattern, data in steps.items():
        pattern_note_steps = {}

        for mult, subdata in data.items():
            # Still need to figure out what the mult data is for, could be undo states
            if mult == "1":

                for note, step in subdata.items():
                    if step['value'] != 127:
                        if int(step['value']) not in pattern_note_steps:
                            pattern_note_steps[int(step['value'])] = {}

                        pattern_note_steps[int(step['value'])][note] = {
                            "pitch": int(pitches[pattern][mult][note]['value']),
                            "velocity": int(velocities[pattern][mult][note]['value']),
                            "gate": int(gates[pattern][mult][note]['value']),
                        }

        track_steps[int(pattern)] = pattern_note_steps

    # It helps later to sort the track data by pattern ID
    track_data = dict(sorted(track_steps.items()))

    # Create an Instrument instance
    # I'd like to offer support for changing this based on user choice
    if is_drum:
        instrument = pretty_midi.Instrument(is_drum=is_drum, program=pretty_midi.instrument_name_to_program("Drums"))
    else:
        instrument = pretty_midi.Instrument(
            program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano")
        )

    # Set the sixteenth note length based on the tempo we derived from the project
    sixteenth_note_duration = 60 / (bpm * 4)
    
    # Keep a cursor so we know when the current pattern ends
    pattern_cursor = 0
    
    # For a list of patterns with data in them
    pattern_list = []

    # Loop through the patterns
    for pattern, step_info in track_data.items():
        
        # Add the pattern ID to the list of patterns with data in them
        if step_info != {}:
            pattern_list.append(pattern)
        
        # Loop through the step info in the patterns
        for step, note_info in step_info.items():
            # Loop through the note info associated with the steps
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
                
        # Increment the cursor by pattern length (defaulting to 64 for now until I can decode pattern length)
        pattern_cursor = pattern_cursor + 64
    
    print(f"Patterns in {track}: {pattern_list}")
    
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
    print(f"Reading project file {project_file_path}")
    parameters_file_path = f"Instruments/{args.instrument}.json"
    print(f"Reading parameters file {parameters_file_path}")

    # Decode the project file
    decoded_project_data = decode_project_file(project_file_path, parameters_file_path)

    # Initialize PrettyMIDI object
    midi_data = pretty_midi.PrettyMIDI()
    for i in range(1, 5):
        print(f"Converting Track {i} to MIDI")
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

    print(f"Decoded project written to {args.json}")
