def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def main():
    data = [1, 2, 3, 4, 5]
    avg = calculate_average(data)
    print(f"Average: {avg}")

if __name__ == "__main__":
    main()