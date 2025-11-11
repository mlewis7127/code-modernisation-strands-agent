"""
Calculator with a couple of errors to test agent self-correction.
The agent should detect these errors and fix them.
"""

class Calculator:
    """Simple calculator class"""
    
    def __init__(self):
        self.result = 0
    
    def add(self, x, y):
        return x + y
    
    def subtract(self, x, y):
        # Error 1: Using undefined variables 'a' and 'b' instead of 'x' and 'y'
        return a - b
    
    def multiply(self, x, y):
        return x * y
    
    def divide(self, x, y):
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y
    
    def power(self, x, y):
        # Error 2: Using undefined function 'pow_function' instead of built-in 'pow'
        return pow_function(x, y)


if __name__ == "__main__":
    calculator = Calculator()
    print(f"5 + 3 = {calculator.add(5, 3)}")
    print(f"10 - 4 = {calculator.subtract(10, 4)}")
    print(f"2 * 3 = {calculator.multiply(2, 3)}")
    print(f"10 / 2 = {calculator.divide(10, 2)}")
    print(f"2 ^ 3 = {calculator.power(2, 3)}")
