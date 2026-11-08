"""Shared message board: append-only list of posts."""
from dataclasses import dataclass


@dataclass
class Post:
    tick: int
    author: int
    kind: str  # "note" | "writeup" | "result"
    text: str


class Board:
    def __init__(self):
        self._posts: list[Post] = []

    def post(self, tick: int, author: int, kind: str, text: str) -> None:
        self._posts.append(Post(tick, author, kind, text))

    def since(self, index: int, exclude: int) -> tuple[list[Post], int]:
        return [p for p in self._posts[index:] if p.author != exclude], len(self._posts)

    def all(self) -> list[Post]:
        return list(self._posts)

    @staticmethod
    def render(posts: list[Post]) -> str:
        return "\n".join(f"[t{p.tick}] agent {p.author} ({p.kind}): {p.text}" for p in posts)
