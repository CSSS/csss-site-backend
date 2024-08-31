from google_api import internals


def test__list_drives():
    try:
        internals._list_shared_drives_2()
    except Exception as e:
        print(f"got {e}")
