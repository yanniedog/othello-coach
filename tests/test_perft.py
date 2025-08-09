import hashlib
from othello_coach.engine.board import start_board
from othello_coach.engine.perft import perft, load_perft_pack, play_moves


def test_perft_depths():
    b = start_board()
    assert perft(b, 1) == 4
    assert perft(b, 2) == 12
    assert perft(b, 3) == 56
    # Classical Othello perft counts from start
    assert perft(b, 4) == 244
    assert perft(b, 5) == 1396
    assert perft(b, 6) == 8200


def test_perft_pack_sha256_depth6():
    pack = load_perft_pack()
    counts = []
    for seq in pack:
        b = play_moves(None, seq)
        # depths 1..6 concatenated
        for d in range(1, 7):
            counts.append(str(perft(b, d)))
    blob = ",".join(counts).encode("ascii")
    sha = hashlib.sha256(blob).hexdigest()
    # Baseline recorded for this pack with current generators
    assert sha == "20a2ca24168cd6160584ab296f1c79ef7689a119bf1077c1e4c63cc43e8e7be9"
