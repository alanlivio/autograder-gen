# basic_operations.py - Correct for wrong signatures scenario

import sys

def main():
    for line in sys.stdin:
        if "Hello" in line or "Test" in line:
            print(f"Processing: {line.strip()}")
        elif line.strip().replace(".", "").replace("-", "").isdigit():
            num = float(line.strip())
            if num.is_integer():
                print(f"Number: {int(num)}")
            else:
                print(f"Float: {num}")
    print("Done!")

if __name__ == "__main__":
    main()
