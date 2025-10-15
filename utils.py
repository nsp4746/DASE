def read_from_file(filepath):
    """
    Reads content from a specified file and returns it.

    Args:
        filepath (str): The path to the file to be read.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If an I/O error occurs during reading.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        raise
    except IOError as e:
        print(f"Error reading file '{filepath}': {e}")
        raise
