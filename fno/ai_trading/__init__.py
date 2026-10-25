"""The AI books' trading runner (story F1t): each live AI book decides in its own sealed routine session from the common
pack and its own private pack; the daily run judges the answer, hands an accepted one to the book's decider (F5, F6)
and commits the D3 run before E3's deadline. The routine side (`python -m fno.ai_trading`) uses only the standard
library, so a routine needs no install to run it."""
