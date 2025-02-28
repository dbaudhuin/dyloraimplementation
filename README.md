# dyloraimplementation
A recreation of DyLoRa: Towards Energy Efficient Dynamic LoRa Transmission Control


This is "Algorithm 1," described in the paper DyLoRa: Towards Energy Efficient Dynamic LoRa Transmission Control. It has two portions: the gateway and the node. 

The gateway portion aggregates the most recent "n" packets (designated as 10 here and 6 in the original paper) and inputs an averaged SNR of all aggregated packets into the DyLoRa algorithm to estimate the packet delivery rate and the energy efficiency at each spreading factor (sf) and transmission power (tp). The most optimal sf and tp combination will be returned by this algorithm, and the gateway portion will transmit these adjusted settings to the node portion.

The node portion applies these changed parameters and subsequently ensures that each sent data packet is acknowledged. If the amount of unacknowledged data packets in a row exceeds "m," then the node will adjust its own parameters to the most robust available.


The original papers "Algorithm 1" provided an excellent overview of their implementation; however, there seemed to have been a few typos. Specifically, what is corrected is the following:
- "br" in line 14 most likely refers to "dr" or "Data Rate" as depicted in equation (2),
- The probability of payload decoding (P<sub>p</sub>) uses the header's length (L<sub>h</sub>) instead of the payload's length (L<sub>p</sub>) for its calculation in line 22. This being a typo is further supported by the fact that L<sub>p</sub> is present in the "GetEE" function's inputs (line 13) but is not actually used.
- The probability of preamble detection (P<sub>pre</sub>) uses a modified version of the probability of symbol error equation in line 25; however, the probability of preamble detection is concerned with **detection** and not **error**. My solution to this is to subtract the given equation from 1 to correctly identify the probability of preamble detection.
- In the ee (energy efficiency) calculation, the raw tp value is used instead of the tp's "Power (mW)" depicted in Table 2: Transmission Power Level and Gain. I believe this is a typo because this same tp value is used as an input to the "Gain" function which is meant to identify the gain a radio will experience when each tp setting is active; therefore, this value is definately a tp value (0, 1, 2, 3, 4, 5, 6, 7) and not a power value to accurately calculate the energy efficiency. This was solved by mapping each tp value to its associated "Power (mW)" value instead and using the power value as the denominator in the energy efficiency calculation.




How users can get started with the project:

Where users can get help with the project:

Who maintains and contributes to the project:
