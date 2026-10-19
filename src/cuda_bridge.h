#ifndef CONQUEST_CUDA_BRIDGE_H
#define CONQUEST_CUDA_BRIDGE_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * CONQUEST Dynamic CUDA Bridge Header
 * Zero-SDK runtime dynamic loader for cuBLAS, cuSOLVER, and cuFFT.
 */

int cq_cuda_init(int myid, int *dev_count);
void cq_cuda_finalize(void);
int cq_cuda_is_available(void);
void cq_cuda_set_device_hint(int hint);

int cq_cusolver_zhegv(int mode_v, int n, void *h_A, int lda, void *h_B, int ldb, double *h_W);

int cq_cublas_dgemm(int op_a, int op_b, int m, int n, int k,
                    double alpha, const double *h_A, int lda,
                    const double *h_B, int ldb,
                    double beta, double *h_C, int ldc);

int cq_cublas_zgemm(int op_a, int op_b, int m, int n, int k,
                    const void *alpha, const void *h_A, int lda,
                    const void *h_B, int ldb,
                    const void *beta, void *h_C, int ldc);

int cq_cufft_3d_z2z(int nx, int ny, int nz, void *h_data, int isign);

#ifdef __cplusplus
}
#endif

#endif /* CONQUEST_CUDA_BRIDGE_H */
