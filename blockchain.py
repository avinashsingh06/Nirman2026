import hashlib
import datetime

class Block:
    def __init__(self, index, emotion, previous_hash):
        self.index = index
        self.timestamp = str(datetime.datetime.now())
        self.emotion = emotion
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        data = str(self.index) + self.timestamp + self.emotion + self.previous_hash
        return hashlib.sha256(data.encode()).hexdigest()


class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block(0, "start", "0")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, emotion):
        prev_block = self.get_latest_block()
        new_block = Block(
            index=len(self.chain),
            emotion=emotion,
            previous_hash=prev_block.hash
        )
        self.chain.append(new_block)

    def verify_chain(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False

            if current.previous_hash != previous.hash:
                return False

        return True

    def get_emotions(self):
        return [block.emotion for block in self.chain if block.emotion != "start"]

    def get_full_chain(self):
        return self.chain