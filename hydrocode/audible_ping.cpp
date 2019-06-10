//
//  audible_ping.cpp
//  hydromathd
//
//  Prints to file normalized samples in an Audacity friendly format for listening on the ears. Should not be on sub.
//
//  Created by Vlad on 11/16/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#include <cstdio>
#include <cstdint>

#include "audible_ping.hpp"
#include "liquid.h"
#include "structs.hpp"

int cheat = 0;
int print_term = 0;

FILE *audible_file;

uint16_t twosComplement(float value)
{
    //Returns the 16 bit two's complement of a float
    
    uint16_t complement;
    
    if(value < 0)
    {
        complement = 65536 + (int16_t)value;
    }
    else
    {
        complement = (int16_t)value;
    }
    
    return complement;
}

void printAudible(triple_sample sample_to_print)
{
    cheat++;
    if(cheat == 4)
    {
        cheat = 0;
    
        //Main function
    
        //printing only 4 * 2 (stereo) = 8 samples on every line
        if(print_term == 4)
        {
            fprintf(audible_file, "\n");
        
            print_term = 0;
        }
    
        fprintf(audible_file, "%.4hx ", twosComplement(sample_to_print.ch2));
        fprintf(audible_file, "%.4hx ", twosComplement(sample_to_print.ch2));
    
        print_term++;
    }
}
