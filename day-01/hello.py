import argparse

def main():
    # 1. Initialize the parser with a helpful description
    parser = argparse.ArgumentParser(
        description="A customizable Hello World CLI script."
    )
    
    # 2. Add the --name flag (defaults to 'World')
    parser.add_argument(
        "-n", "--name",
        type=str,
        default="World",
        help="The name of the person to greet."
    )
    
    # 3. Add the --greeting flag (defaults to 'Hello')
    parser.add_argument(
        "-g", "--greeting",
        type=str,
        default="Hello",
        help="The greeting phrase to use."
    )
    
    # 4. Parse the arguments provided by the user in the terminal
    args = parser.parse_args()
    
    # 5. Output the formatted string to the console
    print(f"{args.greeting}, {args.name}!")

if __name__ == "__main__":
    main()
