from imgstore import new_for_filename

path = "/root/2021-09-26_15-07-37"

def main():
    store = new_for_filename(path)
    metadata = store.get_frame_metadata()
    print(metadata)
    import ipdb; ipdb.set_trace()

main()
