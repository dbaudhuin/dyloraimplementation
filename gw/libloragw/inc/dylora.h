#include <stdio.h>
#include <string.h>
// TODO: 1 UPDATE THIS PATH (DONE I THINK)
#include "loragw_hal.h"
#include <math.h>

// TODO: include LORAGQ_HAL.H to get the specific values for transmission decode ( Will cross this bridge when i get too it.)
#define PREAMBLE_LENGTH 8 // TODO: Preamble Length (In paper mentioned as 8 (Bytes or Symbols); however, there is no clerification 
                          // as to if this is the user defined "n" value or if this is the total (n+4.25) value. 
                          // (Note that "n" is used for 2 user defined values, this "n" refers to the user defined
                          // number in the LoRa radio's firmware.)) Currently my plan is to use "8" as the paper says
                          // HOWEVER, if this messes with my transmission I will use whatever the allinone.py uses.
#define NUM_SF 6 // Number of Spreading Factors
#define NUM_TP 8 // Number of Transmission Powers
#define MAX_NODES 100
#define WINDOW_SIZE 6 // TODO: Change this to the user defined "n" value. (is defined to be 6 in the paper)
#define NODE_ID_NAME_LENGTH 16
#define HEADER_LENGTH 3 // TODO: COME BACK TO THIS (I am setting this to the length of a header in loragw_hal for transmitted packets.)
                        // SO far i believe this is 1 byte; however, I think i will find more information in the 
                        // Update, 1 symbol is SF amount of bits. So we may need to change how we deal with header length. Thankfully all that is contained here.
#define MSG(args...)    fprintf(stderr,"loragw_pkt_logger: " args) /* message that is destined to the user */


typedef struct {
    char node_id[16];
    float snr_values[WINDOW_SIZE];
    int current_sf;
    int current_tp;
    // int missed_pkts;          // Number of values collected so far
    int index;  // Current index in the circular buffer
    int snr_total;
    int current_seq;
} node_history;

typedef struct {
    int sf;
    int tp;
    double energy_efficiency;
} Config;

// This function builds and sends an update packet that tells the node to update its SF and TP.
void send_update_packet(const char* node_id, int new_sf, int new_tp, int seq) {
    struct lgw_pkt_tx_s update_pkt;
    memset(&update_pkt, 0, sizeof(update_pkt));

    
    // TODO: UPDATE THESE TO DYLORA (NEED TO LOOK INTO ONCE WE ARE SENDING DATA, IDEALLTY USE WHAT ALLINONE.PY USES BUT WE CAN RELY ON THAT BC THAT DOESNT ACCOUNT FOR NODES RECIEVING DATA).
    // Set transmission parameters (modify as needed)
    // update_pkt.freq_hz = 868100000; // set frequency appropriate for your system TODO: CHANGE THIS
    update_pkt.freq_hz = 868100000; // set frequency appropriate for your system TODO: CHANGE THIS

    update_pkt.tx_mode = IMMEDIATE; // or TIMESTAMPED if using LBT
    update_pkt.rf_chain = 0;          // use the proper TX chain
    // update_pkt.rf_power = 20;         // power of the packet being sent. (Who cares because we are sending a command packet from the gateway)
    update_pkt.rf_power = 27;         // power of the packet being sent. (Who cares because we are sending a command packet from the gateway)


    // For LoRa modulation (update packet uses LoRa modulation)
    update_pkt.modulation = MOD_LORA;
    update_pkt.bandwidth = BW_125KHZ; // choose the proper bandwidth
    // Set SF to the new spreading factor (converted to the proper datarate value)
    update_pkt.datarate = DR_LORA_SF12;

    // Coding rate doesn’t change for an update command; use a default valid value.
    update_pkt.coderate = CR_LORA_4_5;
    update_pkt.invert_pol = false;
    update_pkt.preamble = PREAMBLE_LENGTH;
    update_pkt.no_header = false;
    update_pkt.no_crc = false;
    
    // Prepare the payload.
    // For example, let the first byte be a command code (e.g., 0xAA)
    // followed by one byte for new_sf and one byte for new_tp.
    if (new_sf == -1 || new_tp == -1) {
        update_pkt.payload[0] = -1; // Command identifier for parameter update TODO: MAKE ALLINONE.PY CHECK FOR BOTH COMMAND TAGS

    } else {
        update_pkt.payload[0] = 0xAA; // Command identifier for parameter update

    }
    update_pkt.payload[1] = (uint8_t)new_sf;
    update_pkt.payload[2] = (uint8_t)new_tp;
    update_pkt.payload[3] = atoi(node_id) & 0x0F; // Target node ID (FROM ASCII TO INT)
    update_pkt.payload[4] = (uint8_t)seq & 0xFF; // sequence
    update_pkt.payload[5] = ((seq >> 8) & 0xFF);
    
    update_pkt.size = 6;
    // MSG("Sending update packet to node %s: New SF = %d, New TP = %d\n", node_id, new_sf, new_tp);
    printf(" - DYLORA UPDATE - Sending update packet to node %s: New SF = %d, New TP = %d\n", node_id, new_sf, new_tp);
    
    // Send the update packet using the HAL method; lgw_send() works similarly in util_tx_test.c.
    int ret = lgw_send(update_pkt);
    if(ret == LGW_HAL_SUCCESS) {
        // MSG("Update packet sent successfully.\n");
        printf(" - DYLORA UPDATE - Update packet sent successfully.\n");

    } else {
        // MSG("Error sending update packet (%d).\n", ret);
        printf(" - DYLORA UPDATE - Error sending update packet (%d)!!!!!!!!!!!!!!!!!!!\n", ret);

    }


}





int SF_LIST[NUM_SF] = {7, 8, 9, 10, 11, 12};
int TP_LIST[NUM_TP] = {0, 1, 2, 3, 4, 5, 6, 7};

double TPGainValues[NUM_TP]   = {8.9, 7.7, 6.4, 5.2, 4.0, 2.8, 1.6, 0.0}; // in dBm
double TPPowerValues[NUM_TP]   = {439, 402, 350, 303, 276, 250, 230, 205}; // in mW
double SFOffsetValues[NUM_SF]  = {-6.3, -6.5, -6.8, -7.3, -8.0, -9.5}; // in dBm

typedef struct update_pkt_t {
    uint8_t header;  // For example, fixed header or command code
    uint8_t new_sf;  // The new spreading factor (SF)
    uint8_t new_tp;  // The new transmission power index
} update_pkt_t;

int chosenSF = -1;
int chosenTP = -1;
double EE = -1;
double TPGain(int tp) {
    return TPGainValues[tp];
}
double TPPower(int tp) {
    return TPPowerValues[tp];
}
// SF Offset uses an offset of 7 because sf values begin at 7. For example, the index would be 0 for sf7.
double SFOffset(int sf) {
    return SFOffsetValues[sf - 7];
}
// This is lines 13 - 28 of "Algorithm 1" in the paper.
Config calculate_ee(double avg_snr, double pkt_bw, int cr, int header_length, int payload_length, int sf, int tp) {
    // MSG("CALCULATE EE - Starting\n");
    Config res;
    res.sf = sf;
    res.tp = tp;
    double data_rate = (sf * pkt_bw) / pow(2.0, sf); // Correction 1: The data rate formula was incorrect in the paper. The paper notes "br" when i believe it should be "dr" or "Data Rate." See README for details.
    // MSG("DataRate: %f\n", data_rate);
    double snr_offset = avg_snr + TPGain(tp) + SFOffset(sf);
    double gamma = pow(10.0, snr_offset / 10.0); // Linearized SNR value fit for calculcations.

    double term1 = sqrt(gamma * pow(2.0, sf + 1));
    double term2 = sqrt(1.386 * sf + 1.154);
    double argument = (term1 - term2) / sqrt(2.0);
    double prob_sym_err = 0.25 * erfc(argument); // Probability of Symbol Error.

    double prob_header_decode = pow(pow(1.0 - prob_sym_err, 4.0) + 3.0 * pow(1.0 - prob_sym_err, 7.0) * prob_sym_err, ((double)header_length / (2.0 * sf)));  // Probability of Header Decode.
    // MSG("Header Decode: %f\n", prob_header_decode);
    double prob_payload_decode;
// Original Version:
    // if (cr == 1 || cr == 2) {
    //     prob_payload_decode = pow(1.0 - prob_sym_err, (double)header_length / sf);
    // } else {
    //     prob_payload_decode = pow(pow(1.0 - prob_sym_err, 4.0) + 3.0 * pow(1.0 - prob_sym_err, 3.0 + cr) * prob_sym_err, (double)header_length / (4.0 * sf));  // Probability of Payload Decode. 
    // }
    if (cr == 1 || cr == 2) {
        prob_payload_decode = pow(1.0 - prob_sym_err, (double)payload_length / sf); // Correction 2: The payload decode formula was incorrect in the paper. The paper notes to use the header length when I believe it should be the payload length. See README for details.
    } else {
        prob_payload_decode = pow(pow(1.0 - prob_sym_err, 4.0) + 3.0 * pow(1.0 - prob_sym_err, 3.0 + cr) * prob_sym_err, (double)payload_length / (4.0 * sf));  // Probability of Payload Decode. Correction 2: The payload decode formula was incorrect in the paper. The paper notes to use the header length when I believe it should be the payload length. See README for details.
    }
    // MSG("Payload Decode: %f\n", prob_payload_decode);

    double SFPrime = sf + log2(PREAMBLE_LENGTH + 4.25); // PREAMBLE_LENGTH is the "n" value associated with the user defined value in the LoRa radio's firmware.
    double term3 = sqrt(gamma * pow(2.0, SFPrime + 1));
    double term4 = sqrt(1.386 * SFPrime + 1.154);
    double argument1 = (term3 - term4) / sqrt(2.0);
    // Original version:
    // prob_preamble_detection = 0.25 * erfc(argument1);
    double prob_preamble_detection = 1.0 - 0.25 * erfc(argument1); // Probability of Preamble Detection. Correction 3: The preamble detection formula was incorrect in the paper. The paper notes does not subtract this result from 1. See README for details.
    // MSG("Preamble Detection: %f\n", prob_preamble_detection);
    double packet_delivery_rate = prob_preamble_detection * prob_header_decode * prob_payload_decode; // Packet Delivery Rate.
    // MSG("Packet Delivery Rate: %f\n", packet_delivery_rate);
    double energy_efficiency = data_rate * (packet_delivery_rate / TPPower(tp)); // Energy Efficiency. Correction 4: The energy efficiency formula was incorrect in the paper. The paper uses the raw tp values and not the actual wattages. See README for details.
    res.energy_efficiency = energy_efficiency;
    // printf("5.1: Energy Efficiency: %f\n", res.energy_efficiency);
    // MSG("CALCULATE EE - Returning\n");
    return res;
}
// This is lines 6 - 11 of "Algorithm 1" in the paper.
Config dylora_algorithm(double avg_snr, double pkt_bw, int cr, int payload_length) {

    printf(" - DYLORA ALGORITHM - Starting\n");
    chosenSF = -1;
    chosenTP = -1; 
    EE = -1;  
    
    int flags = 0;
    Config res;
    for (int i = 0; i < NUM_SF; i++) {
        for (int j = 0; j < NUM_TP; j++) {
            int sf = SF_LIST[i];
            int tp = TP_LIST[j];
            res = calculate_ee(avg_snr, pkt_bw, cr, HEADER_LENGTH, payload_length, sf, tp);
            if ((res.energy_efficiency > EE) && (flags < 10)) {
                EE = res.energy_efficiency;
                chosenSF = res.sf;
                chosenTP = res.tp;
                printf(" - DYLORA ALGORITHM OPTIMAL CONFIG FOUND - Best SF: %d, Best TP: %d, Best EE: %f\n", chosenSF, chosenTP, EE);
                flags++;
            } else if (flags >= 10) {
                printf(" - DYLORA ALGORITHM - Maximum number of flags reached.\n");
                Config new = {chosenSF, chosenTP, EE};
                return new;
            }
        }
    }
    printf(" - DYLORA ALGORITHM - Returning\n");
    Config new = {chosenSF, chosenTP, EE};
    return new;
}