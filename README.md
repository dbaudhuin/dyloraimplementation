# dyloraimplementation
A recreation of DyLoRa: Towards Energy Efficient Dynamic LoRa Transmission Control


This is "Algorithm 1," described in the paper DyLoRa: Towards Energy Efficient Dynamic LoRa Transmission Control. It has two portions: the gateway and the node. 

The gateway portion aggregates the most recent "n" packets (designated as 10 here and 6 in the original paper) and then inputs an averaged SNR of all aggregated packets into the DyLoRa algorithm to estimate the packet delivery rate and the energy efficiency at each spreading factor (sf) and transmission power (tp). The most optimal sf and tp combination will be returned by this algorithm, and the gateway portion will transmit these adjusted settings to the node portion.

The node portion applies these changed parameters and ensures that each sent data packet is acknowledged. If the amount of unacknowledged data packets in a row exceeds "n," then the node will adjust its own parameters to the most robust available.


The original papers "Algorithm 1" provided an excellent overview of their implementation; however, there seemed to have been a few typos. Specifically, what is corrected is the following:
1. "br" in line 14 most likely refers to "dr" or "Data Rate" as depicted in equation (2),
2. The probability of payload decoding (P<sub>p</sub>) uses the header's length (L<sub>h</sub>) instead of the payload's length (L<sub>p</sub>) for its calculation in line 22. This being a typo is further supported by the fact that L<sub>p</sub> is present in the "GetEE" function's inputs (line 13) but is not actually used.
3. The probability of preamble detection (P<sub>pre</sub>) uses a modified version of the probability of symbol error equation in line 25; however, the probability of preamble detection is concerned with **detection** and not **error**. My solution to this is to subtract the given equation from 1 to correctly identify the probability of preamble detection.
4. In the ee (energy efficiency) calculation, the raw tp value is used instead of the tp's "Power (mW)" depicted in Table 2: Transmission Power Level and Gain. I believe this is a typo because this same tp value is used as an input to the "Gain" function which is meant to identify the gain a radio will experience when each tp setting is active; therefore, this value is definately a tp value (0, 1, 2, 3, 4, 5, 6, 7) and not a power value to accurately calculate the energy efficiency. This was solved by mapping each tp value to its associated "Power (mW)" value instead and using the power value as the denominator in the energy efficiency calculation.
- While not explicitly a typo but more of a point of confusion, the paper describes both the amount of aggregated packets used to construct the SNR average and the user-defined LoRa radio preamble value in the firmware as "n." I will not break this naming convention. Instead, I will identify which "n" is referred to when necessary.

Begin by creating a virtual environment in the root directory and then entering it.

    python3 -m venv env
    source env/bin/activate
    
Then, install the required dependencies.

    pip install -r requirements.txt


You can then run the make file to compile both C and C++ versions. Once run, these versions output a results.dat file that can be viewed or fed into "py_runner.py," which turns these results into digestible graphs using matplotlib and numpy. 

With your virtual environment active, run the Python graphing script (edit this file depending on if you want to use resultsc.dat or resultsc++.dat):

    python py_runner.py

The python port can be run (with the virtual environment active) standalone using "dylora.py" or with this graph visualization using "dylora_visual.py." Please note that the standalone version is not updated correctly, as I personally use the graphs to verify my work visually.

    python dylora.py
or

    python dylora_visual.py



Where users can get help with the project:

Who maintains and contributes to the project:
