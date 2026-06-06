# Live plotting and direction polarity notes

This build changes the host logger to run with unbuffered stdout (`python -u`) and changes the GUI plot refresh to 100 ms. The Live Plots tab should now update continuously instead of appearing in large buffered chunks.

The GUI also adds a DIR polarity selector:

- `normal` sends `J` to the Arduino target.
- `inverted` sends `I` to the Arduino target.

Use this if the commanded CW/CCW labels are reversed relative to physical table motion. If the table moves the same physical direction for both CW and CCW commands, check the DIR wire, driver DIR input, common ground, and the assigned Arduino DIR pin. Software inversion can swap directions, but it cannot fix a disconnected or ignored DIR input.

Recommended debug sequence:

1. Set Trial length = `super_short`.
2. Set Telemetry rate = `20 Hz`.
3. Run `D`.
4. Watch the live position and speed plots.
5. If CW is physically reversed, switch DIR polarity and rerun `D`.
