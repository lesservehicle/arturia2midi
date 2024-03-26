from main import decode_project_file, decode_key, load_json_file

def test_decode_project():
    test_project = f"Projects/Sample.KeyStepPro"
    test_device = f"Devices/KeyStepPro.json"

    decoded_project_data = decode_project_file(test_project, test_device)

    if decoded_project_data != {}:
        assert True
    else:
        assert False

def test_decode_key():
    test_device = f"Devices/KeyStepPro.json"
    parameters_data = load_json_file(test_device)
    key = "123_111_1_1_1"
    
    decoded_key = decode_key(key, parameters_data)
    
    if decoded_key == "Seq note velocity":
        assert True
    else:
        assert False
        