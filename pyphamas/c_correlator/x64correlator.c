#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <time.h>
//#include <iostream.h>

//using namespace std;

const int header[4] = {0x0a, 0x00, 0x00, 0x14};
const int input_matrix[8][8] = {
  { 0,  8,  2, 10,  4, 12,  6, 14},
  { 1,  9,  3, 11,  5, 13,  7, 15},
  {16, 24, 18, 26, 20, 28, 22, 30},
  {17, 25, 19, 27, 21, 29, 23, 31},
  {32, 40, 34, 42, 36, 44, 38, 46},
  {33, 41, 35, 43, 37, 45, 39, 47},
  {48, 56, 50, 58, 52, 60, 54, 62},
  {49, 57, 51, 59, 53, 61, 55, 63}
};

#define UDP_HEADER_LENGTH 66
#define GULP_HEADER_LENGTH 24
#define DAQ_HEADER_LENGTH 8								
#define PACKETS_PER_SECOND ((pow(10.0,6.0)/512)*50.0)
#define SECONDS_PER_BATCH 0.25
#define PACKETS_PER_BATCH 10000.0
								
/***********************************************
 * cdouble
 * A typedef struct that represents a complex number
 * by storing two doubles for the real and imaginary
 * parts.
 *
 * Initializing a cdouble
 *    cdouble mydouble;
 *
 * Real Part
 *    double real = mydouble.real;
 *    mydouble.real = 5.6;
 *
 * Imaginary Part
 *    double imag = mydouble.imag;
 *    mydouble.imag = 3.95;
 ***********************************************/
typedef struct complex {
  float real;
  float imag;
} cdouble;

/***********************************************
 * outprod
 * Performs the outer product between two complex
 * vectors (i.e. xy')
 ***********************************************/
void outprod(int length, cdouble * vec1, cdouble * vec2, cdouble * out) {
  int r;
  int c;
  int idx;
  for (r = 0; r < length; r++) {
    for (c = 0; c <= r; c++) {
      idx = r*length + c;
      out[idx].real += vec1[r].real*vec2[c].real + vec1[r].imag*vec2[c].imag;
      out[idx].imag += vec1[r].imag*vec2[c].real - vec1[r].real*vec2[c].imag;
    }
  }
}


/***********************************************
 * vsum
 * Performs a sum between two vectors (i.e. a + b => a)
 ***********************************************/
void vsum(int length, cdouble * a, cdouble * b) {
  int r;
  for (r = 0; r < length; r++) {
    a[r].real += b[r].real;
    a[r].imag += b[r].imag;
  }
}

/***********************************************
 * msum
 * Performs a sum between two matrices (i.e. A + B => A)
 ***********************************************/
void msum(int numrows, int numcols, cdouble * A, cdouble * B) {
  int r;
  int c;
  int idx;
  for (r = 0; r < numrows; r++) {
    for (c = 0; c < numcols; c++) {
      idx = r*numcols + c;
      A[idx].real = A[idx].real + B[idx].real;
      A[idx].imag = A[idx].imag + B[idx].imag;
    }
  }
}

/***********************************************
 * smdiv
 * Performs the division between a matrix
 * and a scalar (i.e. (1/a)*A => A)
 ***********************************************/
void smdiv(int numrows, int numcols, cdouble * A, int a) {
  int r;
  int c;
  int idx;
  double val = 1.0/a;
  for (r = 0; r < numrows; r++) {
    for (c = 0; c < numcols; c++) {
      idx = r*numcols + c;
      A[idx].real = A[idx].real*val;
      A[idx].imag = A[idx].imag*val;
    }
  }
}

double c_abs(cdouble data) {
  return data.real*data.real + data.imag*data.imag;
}

void print_usage() {
  printf("USAGE: correlate input_filename output_filename\n");
  printf("\tinput_filename: A binary file received by the x64 DAQ system\n");
  printf("\toutput_filename: A binary file containing the lower-diagonal portion of the cross-correlation matrices\n");
}

/*
 * File Structure
 *   GULP HEADER (24 bytes)
 *   UDP PACKET 1 HEADER (66 bytes)
 *   DAQ PACKET 1 HEADER (8 bytes)
 *   PACKET 1 DATA (variable number of bytes)
 *   UDP PACKET 2 HEADER (66 bytes)
 *   DAQ PACKET 2 HEADER (8 bytes)
 *   PACKET 2 DATA (variable number of bytes)
 *   ...
 *
 */
int main(int argc, char * argv[]) {
	
  //test_driver();
  //return 0;
  
  // Start Timer
  clock_t tstart, tend;
  tstart = clock();

  if (argc < 3) {
    print_usage();
    return -1;
  }
  
  float seconds_to_skip = 0.0;
  if (argc > 3) {
    seconds_to_skip = atof(argv[3]);
    printf("seconds to skip = %f\n", seconds_to_skip);
  }
  long long int packets_to_skip = seconds_to_skip*PACKETS_PER_SECOND;
  printf("number of packets to skip = %lld\n", packets_to_skip);

  float num_seconds = 0.0;
  int desired_packets = -1;
  if (argc == 5) {
    num_seconds = atof(argv[4]);
    printf("number of seconds: %f\n", num_seconds);
    desired_packets = PACKETS_PER_SECOND*num_seconds;
    printf("number of packets: %i\n", desired_packets);
  }

  // Open File
  FILE * file;
  FILE * outfile;
  file = fopen(argv[1], "rb");
  outfile = fopen(argv[2], "wb");
  if (!file) {
    fprintf(stderr, "Error opening input file %s\n", argv[1]);
    return -1;
  }
  if (!outfile) {
    fprintf(stderr, "Error opening output file %s\n", argv[2]);
  }
  
  // Get File Length
  unsigned long fileLen;
  fseek(file, 0, SEEK_END);
  fileLen=ftell(file);
  fseek(file, 0, SEEK_SET);
  
  printf("File Length (bytes):  %lu\n", fileLen);
  if (fileLen > 1024) {
    printf("File Length (kbytes): %lu\n", fileLen/1024);
  }
  if (fileLen > 1024*1024) {
    printf("File Length (Mbytes): %lu\n", fileLen/1024/1024);
  }
  if (fileLen > 1024*1024*1024) {
    printf("File Length (Gbytes): %lu\n", fileLen/1024/1024/1024);
  }
  
  // Read header information into buffer
  unsigned char * gulp_buffer = malloc(sizeof(unsigned char)*4);
  fread(gulp_buffer, sizeof(unsigned char), 4, file);
  
  int gulp_bytes = 0;
  // printf("%x%x%x%x\n", gulp_buffer[0], gulp_buffer[1], gulp_buffer[2], gulp_buffer[3]);
  if (gulp_buffer[0] == 0xd4 && gulp_buffer[1] == 0xc3 && gulp_buffer[2] == 0xb2 && gulp_buffer[3] == 0xa1) {
    gulp_bytes = GULP_HEADER_LENGTH;
  }
  free(gulp_buffer);
  
  // Rewind file to beginning
  fseek(file, 0, SEEK_SET);
  
  // Extract first header information from file
  int bytes_through_header = gulp_bytes + UDP_HEADER_LENGTH + 8;
  unsigned char * header_buffer = malloc(sizeof(unsigned char)*bytes_through_header);
  fread(header_buffer, sizeof(unsigned char), bytes_through_header, file);
  
  // printf("%x%x%x%x\n", header_buffer[0], header_buffer[1], header_buffer[2], header_buffer[3]);
  
  // Get the first packet's header information
  // This contains the capture parameters (rows, cols, bins, fft length, etc)
  unsigned char header_bytes[8];
  int i;
  for (i = 0; i < 8; i++) {
    header_bytes[i] = header_buffer[gulp_bytes + UDP_HEADER_LENGTH + i];
  }
  free(header_buffer);
  
  // Let MSB = bit 63 and LSB = bit 0
  // header_bytes[0] is bits 63->56
  // header_bytes[1] is bits 55->48
  // header_bytes[2] is bits 47->40
  // header_bytes[3] is bits 39->32
  // 
  // bin_start is bits 63->54
  // bin_end is bits 53->44
  // row_start is bits 43->41
  // row_flag is bit 40
  //     row_flag = 0 means four consecutive rows from row_start
  //     row_flag = 1 means all eight rows
  // col_start is bits 39->37
  // col_end is bits 36->34
  // fft_bits is bits 33->32
  //     fft_bits = 00 means 256 FFT
  //     fft_bits = 01 means 512 FFT
  //     fft_bits = 10 means 1024 FFT
  //     fft_bits = 11 means nothing (yet)
  //     N = 2^(fft_bits + 8)
  int bin_start = (((header_bytes[0] << 8) + header_bytes[1]) >> 6) & 0x3ff;
  int bin_end = ((((header_bytes[1] << 8) + header_bytes[2]) << 2) >> 6) & 0x3ff;
  int row_start = ((header_bytes[2] << 4) >> 5) & 0x7;
  int row_end = row_start + 4*((header_bytes[2] & 0x1) + 1) - 1;
  int col_start = (header_bytes[3] >> 5) & 0x7;
  int col_end = (header_bytes[3] >> 2) & 0x7;
  int fft_length = pow(2, ((header_bytes[3] & 0x3) + 8));
  
  int num_bins = bin_end - bin_start + 1;
  int num_rows = row_end - row_start + 1;
  int num_cols = col_end - col_start + 1;
  int num_eles = num_rows*num_cols;
  
  printf("\nCapture Parameters: %d %d %d %d %d %d %d\n", bin_start, bin_end, row_start, row_end, col_start, col_end, fft_length);
	
  // Calculate the length of the packet's data section (i.e. the I/Q samples)
  int packet_length = num_rows*num_bins*num_cols*8/4;
  // printf("\nPacket Length: %d\n", packet_length);
  
  // Calculate the number of bytes between the start locations of two packets' data sections
  int distance_between_packets = packet_length + UDP_HEADER_LENGTH + DAQ_HEADER_LENGTH;
  // printf("Distance between packets: %d\n", distance_between_packets);
  
  // Calculate the number of packets
  int total_packets = (fileLen - 24)/distance_between_packets;
  int number_packets = total_packets;
  if (desired_packets != -1) {
    number_packets = desired_packets;
  }

  // Calculate the starting byte of the first packet's header
  long long int first_start = gulp_bytes + UDP_HEADER_LENGTH + packets_to_skip*distance_between_packets;
  // printf("Starting byte number of first packet header: %lld\n", first_start);
  
  // Allocate raw data buffer
  int bytes_per_batch = distance_between_packets*PACKETS_PER_BATCH;
  // printf("bytes_per_batch = %d\n", bytes_per_batch);
  unsigned char * buffer = malloc(sizeof(unsigned char)*bytes_per_batch);
  
  // Determine number of batches
  int num_batches = (int)ceil(number_packets/PACKETS_PER_BATCH);
  // printf("num_batches = %d\n", num_batches);
  
  // Initialize a 2D data structure to contain all of the raw data for a single packet
  cdouble * raw_data = (cdouble *)malloc(sizeof(cdouble)*num_bins*num_eles);
  
  // Initialize a 3D data structure to contain the partial correlation matrices for each frequency bin
  // Initialize all values to 0.
  // Additionally, initialize running mean structure
  int b;
  int e;
  int f;
  int idx;
  cdouble * corr_mats = (cdouble *)malloc(sizeof(cdouble)*num_bins*num_eles*num_eles);
  cdouble * mean = (cdouble *)malloc(sizeof(cdouble)*num_bins*num_eles);
  for (b = 0; b < num_bins; b++) {
    for (e = 0; e < num_eles; e++) {
      mean[b*num_eles + e].real = 0.0;
      mean[b*num_eles + e].imag = 0.0;
      for (f = 0; f < num_eles; f++) {
	idx = b*num_eles*num_eles + e*num_eles + f;
	corr_mats[idx].real = 0.0;
	corr_mats[idx].imag = 0.0;
      }
    }
  }
  // printf("allocated correlation matrix\n");
  
  
  // Seek to the first packet location
  fseek(file, 0, SEEK_SET);
  fseek(file, first_start, SEEK_SET);
  
  int n;
  for (n = 0; n < num_batches; n++) {
    // printf("############ Batch %d #############\n", n);
    
    // Read file into buffer
    size_t new_bytes = fread(buffer, sizeof(unsigned char), bytes_per_batch, file);
    float packets_in_batch = new_bytes/distance_between_packets;
    // printf("packets_in_batch = %f, maximum = %f\n", packets_in_batch, PACKETS_PER_BATCH);
    
    // Iterate over all packets and iteratively construct partial correlations
    for (i = 0; i < packets_in_batch; i++) {
      // Get the starting byte for the packet
      int packet_start = i*distance_between_packets;
      
      // Get the ending byte for the packet
      int packet_end = packet_start + packet_length;
      
      // Get the packet number (sanity check more than anything)
      int packet_number = (buffer[packet_start+4] << 24) + (buffer[packet_start+5] << 16) + (buffer[packet_start+6] << 8)+buffer[packet_start+7];
      // printf("packet number = %d\n", packet_number);
      
      // Save the real and imaginary parts of each frequency bin/element combination in the packet
      int j;
      int bin_counter = bin_start;
      int col_counter = col_start;
      int row_counter = row_start;
      for (j = packet_start+8; j < packet_end+8; j+=8) {
	// Calculate bin number
	int bin_number = bin_counter;
	
	// Calculate element numbers
	int cur_col = col_counter - col_start;
	int top_row = row_counter - row_start;
	int ele_number1 = cur_col*num_rows + top_row;
	int ele_number2 = cur_col*num_rows + top_row + 1;
	int ele_number3 = cur_col*num_rows + top_row + 2;
	int ele_number4 = cur_col*num_rows + top_row + 3;
	
	// Extract real and imaginary parts
	// Save data to 2D complex data structure
	raw_data[(bin_number-bin_start)*num_eles+ele_number4].real = (signed char)(buffer[j]);
	raw_data[(bin_number-bin_start)*num_eles+ele_number4].imag = (signed char)(buffer[j+1]);
	
	raw_data[(bin_number-bin_start)*num_eles+ele_number3].real = (signed char)(buffer[j+2]);
	raw_data[(bin_number-bin_start)*num_eles+ele_number3].imag = (signed char)(buffer[j+3]);
	
	raw_data[(bin_number-bin_start)*num_eles+ele_number2].real = (signed char)(buffer[j+4]);
	raw_data[(bin_number-bin_start)*num_eles+ele_number2].imag = (signed char)(buffer[j+5]);
	raw_data[(bin_number-bin_start)*num_eles+ele_number1].real = (signed char)(buffer[j+6]);
	raw_data[(bin_number-bin_start)*num_eles+ele_number1].imag = (signed char)(buffer[j+7]);
	
	// Increment counters to keep track of which row/column/bin we are on
	bin_counter++;
	if (bin_counter > bin_end) {
	  bin_counter = bin_start;
	  row_counter = row_counter + 4;
	  if (row_counter > row_end) {
	    row_counter = row_start;
	    col_counter++;
	    if (col_counter > col_end) {
	      col_counter = col_start; // In theory the loop should terminate here
	    }
	  }
	}
      }
      
      // This is where we start the parallelization
      // Split each bin into a block
      // maybe split the product/sum into threads?
      
      // Compute partial mean and...
      // Perform partial correlation and sum
      for (b = 0; b < num_bins; b++) {
	// Sum to get partial mean
	vsum(num_eles, mean + b*num_eles, raw_data + b*num_eles);
	// Perform outer product xx' and sum
	outprod(num_eles, raw_data + b*num_eles, raw_data + b*num_eles, corr_mats + b*num_eles*num_eles);
      }
    }
  }
  fclose(file);
  
  // Divide by N for mean computation
  smdiv(num_eles, num_bins, mean, number_packets);
  
  // Compute outer product of mean estimate
  cdouble * mean2 = (cdouble *)malloc(sizeof(cdouble)*num_eles*num_eles*num_bins);
  for (b = 0; b < num_bins; b++) {
    outprod(num_eles, mean + b*num_eles, mean + b*num_eles, mean2 + b*num_eles*num_eles);
  }
  
  // printf("smdiv2!\n");
  // Divide by number of packets - 1
  smdiv(num_eles*num_bins, num_eles, corr_mats, number_packets - 1);
  
  // Subtract mean outer product from correlation estimate
  
  int r;
  int c;
  for (b = 0; b < num_bins; b++) {
    for (r = 0; r < num_eles; r++) {
      for (c = 0; c < r; c++) {
	idx = b*num_eles*num_eles + r*num_eles + c;
	corr_mats[idx].real -= mean2[idx].real*number_packets/(number_packets - 1);
	corr_mats[idx].imag -= mean2[idx].imag*number_packets/(number_packets - 1);
      }
    }
  }
  
  
  
	
  // Deallocate the single packet 2D data structure
  free(raw_data);
  
  // Deallocate the buffer
  free(buffer);
  
  // Dump results to file
  fwrite(&bin_start, sizeof(int), 1, outfile);
  fwrite(&bin_end, sizeof(int), 1, outfile);
  fwrite(&row_start, sizeof(int), 1, outfile);
  fwrite(&row_end, sizeof(int), 1, outfile);
  fwrite(&col_start, sizeof(int), 1, outfile);
  fwrite(&col_end, sizeof(int), 1, outfile);
  fwrite(&fft_length, sizeof(int), 1, outfile);
  fwrite(corr_mats, sizeof(cdouble), num_eles*num_eles*num_bins, outfile);
  
  // Close output file
  fclose(outfile);
  free(corr_mats);
  tend = clock();
  double total_time = (double)(tend - tstart) / CLOCKS_PER_SEC;
  printf("Elapsed Time: %f\n", total_time);
  
  //test_driver();
  return 0;
}


void test_driver() {
	puts("Starting\n");
	//vec1 = [0.5 + j0.1, 0.3 + j0.2]
	cdouble vec1[3] = {{0.5, 0.1},
			   {0.3, 0.2},
			   {0.4, 0.7}};
	//vec2 = [0.2 + j0.3, 0.8 + j0.1]
	cdouble vec2[3] = {{0.2, 0.3},
			   {0.8, 0.1},
			   {0.1, 0.9}};

	printf("vec1 = [%f+j%f, %f+j%f, %f+j%f]\n", vec1[0].real, vec1[0].imag, vec1[1].real, vec1[1].imag, vec1[2].real, vec1[2].imag);
	printf("vec2 = [%f+j%f, %f+j%f, %f+j%f]\n", vec2[0].real, vec2[0].imag, vec2[1].real, vec2[1].imag, vec2[2].real, vec2[2].imag);

	cdouble vec3[9];
	cdouble vec4[9];
	
	outprod(3, vec1, vec2, vec3);
	printf("vec1 vec2^H\n");
	printf("%f+%fj\t%f+%fj\t%f+%fj\n", vec3[0].real, vec3[0].imag, vec3[1].real, vec3[1].imag, vec3[2].real, vec3[2].imag);
	printf("%f+%fj\t%f+%fj\t%f+%fj\n", vec3[3].real, vec3[3].imag, vec3[4].real, vec3[4].imag, vec3[5].real, vec3[5].imag);
	printf("%f+%fj\t%f+%fj\t%f+%fj\n\n", vec3[6].real, vec3[6].imag, vec3[7].real, vec3[7].imag, vec3[8].real, vec3[8].imag);
	
	printf("%f+%fj\t%f+%fj\n", vec4[0].real, vec4[0].imag, vec4[1].real, vec4[1].imag);
	printf("%f+%fj\t%f+%fj\n\n", vec4[2].real, vec4[2].imag, vec4[3].real, vec4[3].imag);
	
	msum(3, 3, vec3, vec4);
	printf("%f+%fj\t%f+%fj\t%f+%fj\n", vec3[0].real, vec3[0].imag, vec3[1].real, vec3[1].imag, vec3[2].real, vec3[2].imag);
	printf("%f+%fj\t%f+%fj\t%f+%fj\n", vec3[3].real, vec3[3].imag, vec3[4].real, vec3[4].imag, vec3[5].real, vec3[5].imag);
	printf("%f+%fj\t%f+%fj\t%f+%fj\n\n", vec3[6].real, vec3[6].imag, vec3[7].real, vec3[7].imag, vec3[8].real, vec3[8].imag);
}
