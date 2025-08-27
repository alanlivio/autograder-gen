# Basic operations with syntax error - demonstrates RUNTIME ERROR
import sys

def main():
    # Get input
    text = input().strip()
    number = int(input().strip())
    float_num = float(input().strip()
    
    # Process and output - this will cause syntax error due to missing closing parenthesis above
    print(f"Processing: {text}")
    print(f"Number: {number}")
    print(f"Float: {float_num}")
    print("Done!")

if __name__ == "__main__":
    main()
