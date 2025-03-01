# src/logical_clock.py

class LogicalClock:
    def __init__(self, initial=0):
        """
        Initialize the logical clock with an initial time.
        """
        self.time = initial

    def tick(self):
        """
        Increment the clock for an internal event and return the updated time.
        """
        self.time += 1
        return self.time

    def update(self, received_time):
        """
        Update the logical clock on receiving a message.
        The new time is the maximum of the current time and the received time, plus one.
        """
        self.time = max(self.time, received_time) + 1
        return self.time

if __name__ == "__main__":
    # Quick test of the LogicalClock class functionality.
    clock = LogicalClock()
    print("Initial clock:", clock.time)
    
    # Simulate an internal tick.
    print("After tick:", clock.tick())
    
    # Simulate receiving a message with a logical clock time of 5.
    print("After receiving message with clock 5:", clock.update(5))
    
    # Another internal tick.
    print("After another tick:", clock.tick())
