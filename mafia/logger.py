class GameLogger:
    """Logger that can write to stdout and an optional file."""

    def __init__(self, verbose: bool = False, log_to_file: bool = False, filename: str = "simul.log"):
        self.verbose = verbose
        self.file = open(filename, "w") if log_to_file else None

    def log(self, message: str) -> None:
        if self.verbose:
            print(message)
        if self.file:
            self.file.write(message + "\n")
            self.file.flush()

    def close(self) -> None:
        if self.file:
            self.file.close()

