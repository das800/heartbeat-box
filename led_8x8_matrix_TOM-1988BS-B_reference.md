| Location   | 1   | 2   | 3   | 4   | 5   | 6   | 7   | 8   |
|------------|-----|-----|-----|-----|-----|-----|-----|-----|
| Top Pins   | 1   | 2   | 3   | 4   | 5   | 6   | 7   | 8   |
| Role       | A   | C   | A   | C   | A   | C   | A   | C   |
| Controls   | r2  | cg  | r4  | ce  | r6  | cc  | r8  | ca  |

| Location   | 9   | 10  | 11  | 12  | 13  | 14  | 15  | 16  |
|------------|-----|-----|-----|-----|-----|-----|-----|-----|
| Bottom Pins| 16  | 15  | 14  | 13  | 12  | 11  | 10  | 9   |
| Role       | C   | A   | C   | A   | C   | A   | C   | A   |
| Controls   | ch  | r1  | cf  | r3  | cd  | r5  | cb  | r7  |

Legend:
- A = Anode (needs HIGH for activation)
- C = Cathode (needs LOW for activation)
- r# = controls row number #
- c[letter] = controls column letter

To activate an LED:
1. Set its row's anode pin HIGH
2. Set its column's cathode pin LOW
3. All other pins must be opposite (cathodes HIGH, anodes LOW) to prevent unwanted LED activation

Example - To light up e3 (5th column, 3rd row):
1. Set pin 13 (anode for row 3) HIGH
2. Set pin 4 (cathode for column e) LOW
3. All other pins opposite

Note: Matrix orientation is with LEDs facing away from viewer (looking at pins), serial number at top. Chess notation is used for position reference (columns a-h right to left, rows 1-8 bottom to top).
