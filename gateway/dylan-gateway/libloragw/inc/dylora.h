#include <stdio.h>
#include <string.h>
#include "loragw_hal.h"
#include <math.h>
#include <unistd.h>
// TODO: include LORAGQ_HAL.H to get the specific values for transmission decode ( Will cross this bridge when i get too it.)
#define PREAMBLE_LENGTH 8 // TODO: Preamble Length (In paper mentioned as 8 (Bytes or Symbols); however, there is no clerification 
                          // as to if this is the user defined "n" value or if this is the total (n+4.25) value. 
                          // (Note that "n" is used for 2 user defined values, this "n" refers to the user defined
                          // number in the LoRa radio's firmware.)) Currently my plan is to use "8" as the paper says
                          // HOWEVER, if this messes with my transmission I will use whatever the allinone.py uses.
#define NUM_SF 4 // Number of Spreading Factors (No SF11, SF12)
#define NUM_TP 8 // Number of Transmission Powers
#define MAX_NODES 100
#define WINDOW_SIZE 6 
#define NODE_ID_NAME_LENGTH 16
#define HEADER_LENGTH 3 // TODO: COME BACK TO THIS (I am setting this to the length of a header in loragw_hal for transmitted packets.)
                        // SO far i believe this is 1 byte; however, I think i will find more information in the 
                        // Update, 1 symbol is SF amount of bits. So we may need to change how we deal with header length. Thankfully all that is contained here.


typedef struct {
    char node_id[16];
    float snr_values[WINDOW_SIZE];
    int current_sf; // Current SF index
    int current_tp; // Current TP index
    // int missed_pkts; // Number of values collected so far
    int index;  // Current index in the circular buffer
    int snr_total;
    int current_seq;
} node_history;

typedef struct {
    int sf;
    int tp;
    double energy_efficiency;
} Config;

int SFsDylora[] = {DR_LORA_SF7, DR_LORA_SF8, DR_LORA_SF9, DR_LORA_SF10, DR_LORA_SF11, DR_LORA_SF12};


// This function builds and sends an update packet that tells the node to update its SF and TP.
void send_update_packet(const char* node_id, int new_sf, int new_tp, int seq, int node_sf) {
    struct lgw_pkt_tx_s update_pkt;
    memset(&update_pkt, 0, sizeof(update_pkt)); // fill bad boy with zeros

    // update_pkt.freq_hz = 868100000;
    update_pkt.freq_hz = 904100000;
    // update_pkt.freq_hz = 904300000;
    // update_pkt.freq_hz = 904900000;


    update_pkt.tx_mode = IMMEDIATE;
    update_pkt.rf_chain = 0;
    // update_pkt.rf_power = 20;         
    update_pkt.rf_power = 27;         


    update_pkt.modulation = MOD_LORA;
    // update_pkt.modulation = MOD_UNDEFINED;

    update_pkt.bandwidth = BW_125KHZ; // choose the proper bandwidth
    // Set SF to the new spreading factor (converted to the proper datarate value)

    printf(" - DYLORA UPDATE - Node Given SF (node_sf & sf_idx): %d\n", node_sf);
    switch(node_sf) {        
        case 0:
            update_pkt.datarate = DR_LORA_SF7;
            break;
        case 1:
            update_pkt.datarate = DR_LORA_SF8;
            break;
        case 2:
            update_pkt.datarate = DR_LORA_SF9;
            break;
        case 3:
            update_pkt.datarate = DR_LORA_SF10;
            break;
        case 4:
            update_pkt.datarate = DR_LORA_SF11;
            break;
        case 5:
            update_pkt.datarate = DR_LORA_SF12;
            break;
    }

    // DR_LORA_SF7 (0x02) → 2
    // DR_LORA_SF8 (0x04) → 4
    // DR_LORA_SF9 (0x08) → 8
    // DR_LORA_SF10 (0x10) → 16
    // DR_LORA_SF11 (0x20) → 32
    // DR_LORA_SF12 (0x40) → 64
    // update_pkt.datarate = DR_LORA_SF12; // TODO: FOR TESTING THIS WILL BE 12; HOWEVER THIS NEEDS TO BE DYNAMIC

    printf(" - DYLORA UPDATE - Sending using this SF: %d\n", update_pkt.datarate);
    

    update_pkt.datarate = DR_LORA_SF10; // TODO: REMOVE THIS FORCING SF12 NO MATTER WHAT





    // Coding rate doesn’t change for an update command; use a default valid value.
    update_pkt.coderate = CR_LORA_4_5;
    update_pkt.invert_pol = false;
    update_pkt.preamble = PREAMBLE_LENGTH;
    update_pkt.no_header = false;
    update_pkt.no_crc = false;
    
    // Prepare the payload.
    // The first byte is a command code then one byte for new_sf and one byte for new_tp.
    if (new_sf == -1 || new_tp == -1) {
        update_pkt.payload[0] = -1;

    } else {
        update_pkt.payload[0] = 0xAA; 

    }
    update_pkt.payload[1] = (uint8_t)new_sf;
    update_pkt.payload[2] = (uint8_t)new_tp;
    update_pkt.payload[3] = atoi(node_id) & 0x0F;
    update_pkt.payload[4] = (uint8_t)seq & 0xFF;
    update_pkt.payload[5] = ((seq >> 8) & 0xFF);
    
    update_pkt.size = 6;

    // printf(" - DYLORA UPDATE - Sending update packet to node %s: New SF = %d, New TP = %d\n", node_id, new_sf, new_tp);
    // printf(" - DYLORA UPDATE - Modulation: %d\n", update_pkt.modulation);
    // printf(" - DYLORA UPDATE - Bandwidth: %d\n", update_pkt.bandwidth);
    // printf(" - DYLORA UPDATE - Data Rate: %d\n", update_pkt.datarate);
    // printf(" - DYLORA UPDATE - Coding Rate: %d\n", update_pkt.coderate);
    // printf(" - DYLORA UPDATE - Invert Polarity: %d\n", update_pkt.invert_pol);
    // printf(" - DYLORA UPDATE - Preamble Length: %d\n", update_pkt.preamble);
    // printf(" - DYLORA UPDATE - No Header: %d\n", update_pkt.no_header);
    // printf(" - DYLORA UPDATE - No CRC: %d\n", update_pkt.no_crc);
    


    // if(new_sf != -1 && new_tp != -1){
    //     printf(" - DYLORA UPDATE - Sending update packet to node %s: New SF = %d, New TP = %d\n", node_id, new_sf, new_tp);
    // } else {
    //     printf(" - DYLORA UPDATE - Sending ack packet to node %s.\n\n", node_id);
    // }
    
    // Send the update packet using the HAL method; lgw_send() works similarly in util_tx_test.c.
    sleep(5);
    int ret = lgw_send(update_pkt);
    if(ret == LGW_HAL_SUCCESS) {
        printf("\n - DYLORA UPDATE - Update/Ack packet sent successfully.\n");

    } else {
        printf("\n - DYLORA UPDATE - Error sending update packet!!!!!!!!!!!!!!!!!!!\n");

    }


}





int SF_LIST[NUM_SF] = {7, 8, 9, 10, 11, 12};
int TP_LIST[NUM_TP] = {0, 1, 2, 3, 4, 5, 6, 7};

double TPGainValues[NUM_TP]   = {8.9, 7.7, 6.4, 5.2, 4.0, 2.8, 1.6, 0.0}; // in dBm
double TPPowerValues[NUM_TP]   = {439, 402, 350, 303, 276, 250, 230, 205}; // in mW TODO MAKE THIS SPECIFIC TO OUR PIs
double SFOffsetValues[NUM_SF]  = {-6.3, -6.5, -6.8, -7.3, -8.0, -9.5}; // in dBm

int chosenSF = -1;
int chosenTP = -1;
double EE = -1;

// This is lines 13 - 28 of "Algorithm 1" in the paper.
Config calculate_ee(double avg_snr, double pkt_bw, int cr, int header_length, int payload_length, int sf, int tp) {
    Config res;
    res.sf = sf;
    res.tp = tp;
    double data_rate = (sf * pkt_bw) / pow(2.0, sf); // Correction 1: The data rate formula was incorrect in the paper. The paper notes "br" when i believe it should be "dr" or "Data Rate." See README for details.
    double snr_offset = avg_snr + TPGainValues[tp] + SFOffsetValues[sf - 7];
    double gamma = pow(10.0, snr_offset / 10.0); // Linearized SNR value fit for calculcations.

    double term1 = sqrt(gamma * pow(2.0, sf + 1));
    double term2 = sqrt(1.386 * sf + 1.154);
    double argument = (term1 - term2) / sqrt(2.0);
    double prob_sym_err = 0.25 * erfc(argument); // Probability of Symbol Error.

    double prob_header_decode = pow(pow(1.0 - prob_sym_err, 4.0) + 3.0 * pow(1.0 - prob_sym_err, 7.0) * prob_sym_err, ((double)header_length / (2.0 * sf)));  // Probability of Header Decode.
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

    double SFPrime = sf + log2(PREAMBLE_LENGTH + 4.25); // PREAMBLE_LENGTH is the "n" value associated with the user defined value in the LoRa radio's firmware.
    double term3 = sqrt(gamma * pow(2.0, SFPrime + 1));
    double term4 = sqrt(1.386 * SFPrime + 1.154);
    double argument1 = (term3 - term4) / sqrt(2.0);
    // Original version:
    // prob_preamble_detection = 0.25 * erfc(argument1);
    double prob_preamble_detection = 1.0 - 0.25 * erfc(argument1); // Probability of Preamble Detection. Correction 3: The preamble detection formula was incorrect in the paper. The paper notes does not subtract this result from 1. See README for details.
    double packet_delivery_rate = prob_preamble_detection * prob_header_decode * prob_payload_decode; // Packet Delivery Rate.
    double energy_efficiency = data_rate * (packet_delivery_rate / TPPowerValues[tp]); // Energy Efficiency. Correction 4: The energy efficiency formula was incorrect in the paper. The paper uses the raw tp values and not the actual wattages. See README for details.
    res.energy_efficiency = energy_efficiency;
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