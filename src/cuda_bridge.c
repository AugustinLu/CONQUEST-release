/*
 * CONQUEST Dynamic CUDA Bridge
 *
 * Loads cudart / cuBLAS / cuSOLVER / cuFFT at run time (no CUDA SDK or nvcc
 * needed at build time) and exposes a small C ABI used by cuda_module.f90.
 * Every entry point returns 0 on success and non-zero on any failure, in
 * which case the host data is left untouched and the Fortran caller falls
 * back to the CPU (OpenBLAS / ScaLAPACK / FFTW) path.
 *
 * Library search order (all libraries are taken from the same directory):
 *   1. $CONQUEST_CUDA_PATH
 *   2. $CUDA_PATH/bin  (CUDA toolkit installer sets this on Windows)
 *   3. the normal system search path (PATH / LD_LIBRARY_PATH)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "cuda_bridge.h"

#ifdef _WIN32
#include <windows.h>
typedef HMODULE lib_handle_t;
#define GET_SYM(h, name) GetProcAddress(h, name)
#define CLOSE_LIB(h) FreeLibrary(h)
#define PATH_SEP "\\"

static CRITICAL_SECTION g_cuda_lock;
static int g_lock_initialized = 0;
#define INIT_CUDA_LOCK() do { if (!g_lock_initialized) { InitializeCriticalSection(&g_cuda_lock); g_lock_initialized = 1; } } while(0)
#define ENTER_CUDA_LOCK() EnterCriticalSection(&g_cuda_lock)
#define LEAVE_CUDA_LOCK() LeaveCriticalSection(&g_cuda_lock)
#define DELETE_CUDA_LOCK() do { if (g_lock_initialized) { DeleteCriticalSection(&g_cuda_lock); g_lock_initialized = 0; } } while(0)

static lib_handle_t load_lib(const char *dir, const char *name) {
    if (dir == NULL) return LoadLibraryA(name);
    char full[2048];
    snprintf(full, sizeof(full), "%s" PATH_SEP "%s", dir, name);
    /* ALTERED_SEARCH_PATH lets dependent DLLs (e.g. cublasLt) resolve from the same dir */
    return LoadLibraryExA(full, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
}

static double wall_time(void) {
    static LARGE_INTEGER freq = {0};
    LARGE_INTEGER now;
    if (freq.QuadPart == 0) QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&now);
    return (double)now.QuadPart / (double)freq.QuadPart;
}

#else
#include <dlfcn.h>
#include <pthread.h>
#include <time.h>
typedef void* lib_handle_t;
#define GET_SYM(h, name) dlsym(h, name)
#define CLOSE_LIB(h) dlclose(h)
#define PATH_SEP "/"

static pthread_mutex_t g_cuda_lock = PTHREAD_MUTEX_INITIALIZER;
#define INIT_CUDA_LOCK() ((void)0)
#define ENTER_CUDA_LOCK() pthread_mutex_lock(&g_cuda_lock)
#define LEAVE_CUDA_LOCK() pthread_mutex_unlock(&g_cuda_lock)
#define DELETE_CUDA_LOCK() ((void)0)

static lib_handle_t load_lib(const char *dir, const char *name) {
    if (dir == NULL) return dlopen(name, RTLD_NOW | RTLD_GLOBAL);
    char full[2048];
    snprintf(full, sizeof(full), "%s" PATH_SEP "%s", dir, name);
    return dlopen(full, RTLD_NOW | RTLD_GLOBAL);
}

static double wall_time(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + 1.0e-9 * (double)ts.tv_nsec;
}
#endif

typedef struct {
    double x; // real
    double y; // imag
} cq_cplx_t;

typedef int cudaError_t;
typedef void* cublasHandle_t;
typedef void* cusolverDnHandle_t;
typedef int cufftHandle;

#define CUDA_SUCCESS 0
#define CUBLAS_STATUS_SUCCESS 0
#define CUSOLVER_STATUS_SUCCESS 0
#define CUFFT_SUCCESS 0

#define CUBLAS_OP_N 0
#define CUBLAS_OP_T 1
#define CUBLAS_OP_C 2

#define CUBLAS_FILL_MODE_LOWER 0
#define CUBLAS_FILL_MODE_UPPER 1

#define CUSOLVER_EIG_TYPE_1 1
#define CUSOLVER_EIG_MODE_NOVECTOR 0
#define CUSOLVER_EIG_MODE_VECTOR 1

#define CUFFT_FORWARD -1
#define CUFFT_INVERSE 1
#define CUFFT_Z2Z 0x69

#define cudaMemcpyHostToDevice 1
#define cudaMemcpyDeviceToHost 2

// Function pointer signatures
typedef cudaError_t (*pfn_cudaGetDeviceCount)(int*);
typedef cudaError_t (*pfn_cudaSetDevice)(int);
typedef cudaError_t (*pfn_cudaDeviceSynchronize)(void);
typedef cudaError_t (*pfn_cudaMalloc)(void**, size_t);
typedef cudaError_t (*pfn_cudaFree)(void*);
typedef cudaError_t (*pfn_cudaMemcpy)(void*, const void*, size_t, int);
typedef cudaError_t (*pfn_cudaMemGetInfo)(size_t*, size_t*);
typedef cudaError_t (*pfn_cudaRuntimeGetVersion)(int*);

typedef int (*pfn_cublasCreate)(cublasHandle_t*);
typedef int (*pfn_cublasDestroy)(cublasHandle_t);
typedef int (*pfn_cublasDgemm)(cublasHandle_t, int, int, int, int, int,
                               const double*, const double*, int,
                               const double*, int, const double*,
                               double*, int);
typedef int (*pfn_cublasZgemm)(cublasHandle_t, int, int, int, int, int,
                               const void*, const void*, int,
                               const void*, int, const void*,
                               void*, int);

typedef int (*pfn_cusolverDnCreate)(cusolverDnHandle_t*);
typedef int (*pfn_cusolverDnDestroy)(cusolverDnHandle_t);
typedef int (*pfn_cusolverDnZhegvd_bufferSize)(cusolverDnHandle_t, int, int, int, int,
                                               const void*, int, const void*, int,
                                               const double*, int*);
typedef int (*pfn_cusolverDnZhegvd)(cusolverDnHandle_t, int, int, int, int,
                                    void*, int, void*, int,
                                    double*, void*, int, int*);

typedef int (*pfn_cufftPlan3d)(cufftHandle*, int, int, int, int);
typedef int (*pfn_cufftExecZ2Z)(cufftHandle, void*, void*, int);
typedef int (*pfn_cufftDestroy)(cufftHandle);

// Internal state
static int g_cuda_initialized = 0;
static int g_cuda_available = 0;
static int g_myid = 0;

static lib_handle_t h_cudart = NULL;
static lib_handle_t h_cublas = NULL;
static lib_handle_t h_cusolver = NULL;
static lib_handle_t h_cufft = NULL;

static pfn_cudaGetDeviceCount fn_cudaGetDeviceCount = NULL;
static pfn_cudaSetDevice fn_cudaSetDevice = NULL;
static pfn_cudaDeviceSynchronize fn_cudaDeviceSynchronize = NULL;
static pfn_cudaMalloc fn_cudaMalloc = NULL;
static pfn_cudaFree fn_cudaFree = NULL;
static pfn_cudaMemcpy fn_cudaMemcpy = NULL;
static pfn_cudaMemGetInfo fn_cudaMemGetInfo = NULL;
static pfn_cudaRuntimeGetVersion fn_cudaRuntimeGetVersion = NULL;

static pfn_cublasCreate fn_cublasCreate = NULL;
static pfn_cublasDestroy fn_cublasDestroy = NULL;
static pfn_cublasDgemm fn_cublasDgemm = NULL;
static pfn_cublasZgemm fn_cublasZgemm = NULL;

static pfn_cusolverDnCreate fn_cusolverDnCreate = NULL;
static pfn_cusolverDnDestroy fn_cusolverDnDestroy = NULL;
static pfn_cusolverDnZhegvd_bufferSize fn_cusolverDnZhegvd_bufferSize = NULL;
static pfn_cusolverDnZhegvd fn_cusolverDnZhegvd = NULL;

static pfn_cufftPlan3d fn_cufftPlan3d = NULL;
static pfn_cufftExecZ2Z fn_cufftExecZ2Z = NULL;
static pfn_cufftDestroy fn_cufftDestroy = NULL;

static cublasHandle_t g_cublas = NULL;
static cusolverDnHandle_t g_cusolver = NULL;

// Persistent device buffer pool to avoid cudaMalloc/cudaFree during SCF
static void *d_pool_A = NULL;
static size_t d_pool_A_bytes = 0;

static void *d_pool_B = NULL;
static size_t d_pool_B_bytes = 0;

static void *d_pool_C = NULL;
static size_t d_pool_C_bytes = 0;

static void *d_pool_work = NULL;
static size_t d_pool_work_bytes = 0;

static void *d_pool_W = NULL;
static size_t d_pool_W_bytes = 0;

static int *d_pool_info = NULL;

// FFT plan cache
static cufftHandle g_cached_fft_plan = 0;
static int g_have_fft_plan = 0;
static int g_cached_fft_nx = 0;
static int g_cached_fft_ny = 0;
static int g_cached_fft_nz = 0;

// Usage statistics (printed by cq_cuda_finalize on rank 0)
enum { ST_ZHEGV = 0, ST_DGEMM, ST_ZGEMM, ST_FFT, ST_N };
static const char *st_names[ST_N] = {"cuSOLVER zhegvd", "cuBLAS dgemm", "cuBLAS zgemm", "cuFFT 3D z2z"};
static long st_calls[ST_N] = {0};
static long st_fail[ST_N] = {0};
static double st_time[ST_N] = {0.0};
static double st_flops[ST_N] = {0.0};

static int ensure_device_buffer(void **ptr, size_t *cur_bytes, size_t req_bytes) {
    if (req_bytes == 0) req_bytes = 16;
    if (*ptr != NULL && *cur_bytes >= req_bytes) return 0;
    if (*ptr != NULL) {
        fn_cudaFree(*ptr);
        *ptr = NULL;
        *cur_bytes = 0;
    }
    // Allocate with 25% extra headroom to avoid frequent reallocations
    size_t alloc_bytes = req_bytes + (req_bytes / 4);
    if (fn_cudaMalloc(ptr, alloc_bytes) == CUDA_SUCCESS) {
        *cur_bytes = alloc_bytes;
        return 0;
    }
    *ptr = NULL;
    if (fn_cudaMalloc(ptr, req_bytes) == CUDA_SUCCESS) {
        *cur_bytes = req_bytes;
        return 0;
    }
    *ptr = NULL;
    *cur_bytes = 0;
    return -1;
}

static void unload_all(void) {
    if (h_cufft) CLOSE_LIB(h_cufft);
    if (h_cusolver) CLOSE_LIB(h_cusolver);
    if (h_cublas) CLOSE_LIB(h_cublas);
    if (h_cudart) CLOSE_LIB(h_cudart);
    h_cufft = h_cusolver = h_cublas = h_cudart = NULL;
}

static lib_handle_t load_first(const char *dir, const char *names[], int n) {
    for (int i = 0; i < n; i++) {
        lib_handle_t h = load_lib(dir, names[i]);
        if (h) return h;
    }
    return NULL;
}

// Try to load a consistent set of CUDA libraries from one directory (NULL = system search)
static int load_cuda_libs(const char *dir) {
#ifdef _WIN32
    const char *cudart_names[]   = {"cudart64_12.dll", "cudart64_110.dll", "cudart64_11.dll", "cudart64_101.dll"};
    const char *cublas_names[]   = {"cublas64_12.dll", "cublas64_11.dll", "cublas64_10.dll"};
    const char *cusolver_names[] = {"cusolver64_11.dll", "cusolver64_12.dll", "cusolver64_10.dll"};
    const char *cufft_names[]    = {"cufft64_11.dll", "cufft64_10.dll", "cufft64_12.dll"};
#else
    const char *cudart_names[]   = {"libcudart.so", "libcudart.so.12", "libcudart.so.11.0"};
    const char *cublas_names[]   = {"libcublas.so", "libcublas.so.12", "libcublas.so.11"};
    const char *cusolver_names[] = {"libcusolver.so", "libcusolver.so.11", "libcusolver.so.12"};
    const char *cufft_names[]    = {"libcufft.so", "libcufft.so.11", "libcufft.so.10"};
#endif
    h_cudart = load_first(dir, cudart_names, (int)(sizeof(cudart_names)/sizeof(cudart_names[0])));
    h_cublas = load_first(dir, cublas_names, (int)(sizeof(cublas_names)/sizeof(cublas_names[0])));
    h_cusolver = load_first(dir, cusolver_names, (int)(sizeof(cusolver_names)/sizeof(cusolver_names[0])));
    h_cufft = load_first(dir, cufft_names, (int)(sizeof(cufft_names)/sizeof(cufft_names[0])));
    if (h_cudart && h_cublas && h_cusolver) return 1;
    unload_all();
    return 0;
}

int cq_cuda_init(int myid, int *dev_count_out) {
    if (dev_count_out) *dev_count_out = 0;
    if (g_cuda_initialized) return g_cuda_available;
    g_cuda_initialized = 1;
    g_cuda_available = 0;
    g_myid = myid;

    const char *found_dir = NULL;
    char cuda_bin[2048];
    const char *env_cq = getenv("CONQUEST_CUDA_PATH");
    const char *env_cuda = getenv("CUDA_PATH");
    int ok = 0;
    if (env_cq && env_cq[0]) {
        ok = load_cuda_libs(env_cq);
        if (ok) found_dir = env_cq;
    }
    if (!ok && env_cuda && env_cuda[0]) {
        snprintf(cuda_bin, sizeof(cuda_bin), "%s" PATH_SEP "bin", env_cuda);
        ok = load_cuda_libs(cuda_bin);
        if (ok) found_dir = cuda_bin;
    }
    if (!ok) {
        ok = load_cuda_libs(NULL);
        if (ok) found_dir = "(system search path)";
    }
    if (!ok) {
        if (myid == 0) {
            printf("[CONQUEST CUDA Bridge] CUDA libraries (cudart/cublas/cusolver) not found; using CPU.\n"
                   "                       Set CONQUEST_CUDA_PATH to the directory holding the CUDA DLLs.\n");
        }
        return 0;
    }

    fn_cudaGetDeviceCount = (pfn_cudaGetDeviceCount)GET_SYM(h_cudart, "cudaGetDeviceCount");
    fn_cudaSetDevice = (pfn_cudaSetDevice)GET_SYM(h_cudart, "cudaSetDevice");
    fn_cudaDeviceSynchronize = (pfn_cudaDeviceSynchronize)GET_SYM(h_cudart, "cudaDeviceSynchronize");
    fn_cudaMalloc = (pfn_cudaMalloc)GET_SYM(h_cudart, "cudaMalloc");
    fn_cudaFree = (pfn_cudaFree)GET_SYM(h_cudart, "cudaFree");
    fn_cudaMemcpy = (pfn_cudaMemcpy)GET_SYM(h_cudart, "cudaMemcpy");
    fn_cudaMemGetInfo = (pfn_cudaMemGetInfo)GET_SYM(h_cudart, "cudaMemGetInfo");
    fn_cudaRuntimeGetVersion = (pfn_cudaRuntimeGetVersion)GET_SYM(h_cudart, "cudaRuntimeGetVersion");

    fn_cublasCreate = (pfn_cublasCreate)GET_SYM(h_cublas, "cublasCreate_v2");
    fn_cublasDestroy = (pfn_cublasDestroy)GET_SYM(h_cublas, "cublasDestroy_v2");
    fn_cublasDgemm = (pfn_cublasDgemm)GET_SYM(h_cublas, "cublasDgemm_v2");
    fn_cublasZgemm = (pfn_cublasZgemm)GET_SYM(h_cublas, "cublasZgemm_v2");

    fn_cusolverDnCreate = (pfn_cusolverDnCreate)GET_SYM(h_cusolver, "cusolverDnCreate");
    fn_cusolverDnDestroy = (pfn_cusolverDnDestroy)GET_SYM(h_cusolver, "cusolverDnDestroy");
    fn_cusolverDnZhegvd_bufferSize = (pfn_cusolverDnZhegvd_bufferSize)GET_SYM(h_cusolver, "cusolverDnZhegvd_bufferSize");
    fn_cusolverDnZhegvd = (pfn_cusolverDnZhegvd)GET_SYM(h_cusolver, "cusolverDnZhegvd");

    if (h_cufft) {
        fn_cufftPlan3d = (pfn_cufftPlan3d)GET_SYM(h_cufft, "cufftPlan3d");
        fn_cufftExecZ2Z = (pfn_cufftExecZ2Z)GET_SYM(h_cufft, "cufftExecZ2Z");
        fn_cufftDestroy = (pfn_cufftDestroy)GET_SYM(h_cufft, "cufftDestroy");
        if (!fn_cufftPlan3d || !fn_cufftExecZ2Z || !fn_cufftDestroy) {
            fn_cufftPlan3d = NULL; fn_cufftExecZ2Z = NULL; fn_cufftDestroy = NULL;
        }
    }

    if (!fn_cudaGetDeviceCount || !fn_cudaSetDevice || !fn_cudaMalloc || !fn_cudaFree || !fn_cudaMemcpy ||
        !fn_cublasCreate || !fn_cublasDestroy || !fn_cublasDgemm || !fn_cublasZgemm ||
        !fn_cusolverDnCreate || !fn_cusolverDnDestroy || !fn_cusolverDnZhegvd_bufferSize || !fn_cusolverDnZhegvd) {
        if (myid == 0) {
            printf("[CONQUEST CUDA Bridge] Incomplete CUDA symbols in %s; using CPU.\n", found_dir);
        }
        unload_all();
        return 0;
    }

    int dev_count = 0;
    if (fn_cudaGetDeviceCount(&dev_count) != CUDA_SUCCESS || dev_count <= 0) {
        if (myid == 0) {
            printf("[CONQUEST CUDA Bridge] No usable CUDA device detected; using CPU.\n");
        }
        unload_all();
        return 0;
    }
    if (dev_count_out) *dev_count_out = dev_count;

    int device_id = myid % dev_count;
    if (fn_cudaSetDevice(device_id) != CUDA_SUCCESS ||
        fn_cublasCreate(&g_cublas) != CUBLAS_STATUS_SUCCESS) {
        if (myid == 0) printf("[CONQUEST CUDA Bridge] cuBLAS initialisation failed; using CPU.\n");
        g_cublas = NULL;
        return 0;
    }
    if (fn_cusolverDnCreate(&g_cusolver) != CUSOLVER_STATUS_SUCCESS) {
        if (myid == 0) printf("[CONQUEST CUDA Bridge] cuSOLVER initialisation failed; using CPU.\n");
        fn_cublasDestroy(g_cublas);
        g_cublas = NULL;
        g_cusolver = NULL;
        return 0;
    }
    if (fn_cudaMalloc((void**)&d_pool_info, sizeof(int)) != CUDA_SUCCESS) {
        d_pool_info = NULL;
        fn_cusolverDnDestroy(g_cusolver);
        fn_cublasDestroy(g_cublas);
        g_cusolver = NULL;
        g_cublas = NULL;
        return 0;
    }

    INIT_CUDA_LOCK();
    g_cuda_available = 1;

    if (myid == 0) {
        size_t free_b = 0, total_b = 0;
        int rt_ver = 0;
        if (fn_cudaMemGetInfo) fn_cudaMemGetInfo(&free_b, &total_b);
        if (fn_cudaRuntimeGetVersion) fn_cudaRuntimeGetVersion(&rt_ver);
        printf("--------------------------------------------------------------------\n");
        printf(" [CONQUEST CUDA GPU Bridge] initialised\n");
        printf("   Libraries         : %s (CUDA runtime %d.%d)\n", found_dir, rt_ver / 1000, (rt_ver % 1000) / 10);
        printf("   Active GPU Device : %d (of %d available)\n", device_id, dev_count);
        printf("   GPU VRAM Capacity : %.2f GB (Free: %.2f GB)\n",
               (double)total_b / (1024.0*1024.0*1024.0), (double)free_b / (1024.0*1024.0*1024.0));
        printf("   Offload targets   : cuSOLVER zhegvd%s%s\n", ", cuBLAS gemm", fn_cufftExecZ2Z ? ", cuFFT 3D z2z" : "");
        printf("--------------------------------------------------------------------\n");
        fflush(stdout);
    }

    return 1;
}

int cq_cuda_is_available(void) {
    return g_cuda_available;
}

static void print_stats(void) {
    int any = 0;
    for (int i = 0; i < ST_N; i++) if (st_calls[i] || st_fail[i]) any = 1;
    printf("--------------------------------------------------------------------\n");
    printf(" [CONQUEST CUDA GPU Bridge] usage on rank %d\n", g_myid);
    if (!any) {
        printf("   No operation was offloaded to the GPU (all below size thresholds).\n");
    } else {
        printf("   %-16s %10s %8s %12s %10s\n", "routine", "calls", "failed", "time (s)", "GFLOP/s");
        for (int i = 0; i < ST_N; i++) {
            if (!st_calls[i] && !st_fail[i]) continue;
            double gf = (st_time[i] > 0.0 && st_flops[i] > 0.0) ? st_flops[i] / st_time[i] * 1.0e-9 : 0.0;
            printf("   %-16s %10ld %8ld %12.3f %10.1f\n", st_names[i], st_calls[i], st_fail[i], st_time[i], gf);
        }
        printf("   (times include host<->device transfers)\n");
    }
    printf("--------------------------------------------------------------------\n");
    fflush(stdout);
}

void cq_cuda_finalize(void) {
    if (!g_cuda_available) return;

    if (g_myid == 0) print_stats();

    if (g_have_fft_plan && fn_cufftDestroy) {
        fn_cufftDestroy(g_cached_fft_plan);
        g_have_fft_plan = 0;
    }

    if (d_pool_A) fn_cudaFree(d_pool_A);
    if (d_pool_B) fn_cudaFree(d_pool_B);
    if (d_pool_C) fn_cudaFree(d_pool_C);
    if (d_pool_work) fn_cudaFree(d_pool_work);
    if (d_pool_W) fn_cudaFree(d_pool_W);
    if (d_pool_info) fn_cudaFree(d_pool_info);

    d_pool_A = d_pool_B = d_pool_C = d_pool_work = d_pool_W = NULL;
    d_pool_info = NULL;
    d_pool_A_bytes = d_pool_B_bytes = d_pool_C_bytes = d_pool_work_bytes = d_pool_W_bytes = 0;

    if (g_cublas) fn_cublasDestroy(g_cublas);
    if (g_cusolver) fn_cusolverDnDestroy(g_cusolver);
    g_cublas = NULL;
    g_cusolver = NULL;

    DELETE_CUDA_LOCK();

    g_cuda_available = 0;
    g_cuda_initialized = 0;
}

#define H2D(dst, src, bytes) (fn_cudaMemcpy((dst), (src), (bytes), cudaMemcpyHostToDevice) == CUDA_SUCCESS)
#define D2H(dst, src, bytes) (fn_cudaMemcpy((dst), (src), (bytes), cudaMemcpyDeviceToHost) == CUDA_SUCCESS)

/*
 * Generalized Complex Hermitian Eigensolver via cuSOLVER:
 *   A * x = lambda * B * x   (upper triangles of A and B are referenced)
 * Arguments:
 *   mode_v: 1 for compute eigenvectors, 0 for eigenvalues only
 *   n: matrix dimension
 *   h_A: complex Hermitian matrix A (lda x n); on exit holds eigenvectors if mode_v=1
 *   lda: leading dimension of A
 *   h_B: complex Hermitian positive definite overlap B (ldb x n); unchanged on exit
 *   ldb: leading dimension of B
 *   h_W: output real eigenvalues array of length n
 * Returns:
 *   0 on success, non-zero on error (host arrays then untouched).
 */
int cq_cusolver_zhegv(int mode_v, int n, void *h_A, int lda, void *h_B, int ldb, double *h_W) {
    if (!g_cuda_available || !g_cusolver) return -1;
    if (n <= 0) return 0;
    if (lda < n || ldb < n) return -4;

    ENTER_CUDA_LOCK();
    double t0 = wall_time();
    int ret = 0;

    size_t a_bytes = (size_t)lda * n * sizeof(cq_cplx_t);
    size_t b_bytes = (size_t)ldb * n * sizeof(cq_cplx_t);
    size_t w_bytes = (size_t)n * sizeof(double);

    if (ensure_device_buffer(&d_pool_A, &d_pool_A_bytes, a_bytes) ||
        ensure_device_buffer(&d_pool_B, &d_pool_B_bytes, b_bytes) ||
        ensure_device_buffer(&d_pool_W, &d_pool_W_bytes, w_bytes)) {
        ret = -2; goto done;
    }

    if (!H2D(d_pool_A, h_A, a_bytes) || !H2D(d_pool_B, h_B, b_bytes)) { ret = -5; goto done; }

    int jobz = (mode_v != 0) ? CUSOLVER_EIG_MODE_VECTOR : CUSOLVER_EIG_MODE_NOVECTOR;
    int uplo = CUBLAS_FILL_MODE_UPPER;
    int itype = CUSOLVER_EIG_TYPE_1;

    int lwork = 0;
    int stat = fn_cusolverDnZhegvd_bufferSize(g_cusolver, itype, jobz, uplo, n,
                                              d_pool_A, lda, d_pool_B, ldb,
                                              (const double*)d_pool_W, &lwork);
    if (stat != CUSOLVER_STATUS_SUCCESS) { ret = 1000 + stat; goto done; }

    if (ensure_device_buffer(&d_pool_work, &d_pool_work_bytes, (size_t)lwork * sizeof(cq_cplx_t))) {
        ret = -3; goto done;
    }

    stat = fn_cusolverDnZhegvd(g_cusolver, itype, jobz, uplo, n,
                               d_pool_A, lda, d_pool_B, ldb,
                               (double*)d_pool_W, d_pool_work, lwork, d_pool_info);
    if (stat != CUSOLVER_STATUS_SUCCESS) { ret = 1000 + stat; goto done; }

    int dev_info = -1;
    if (!D2H(&dev_info, d_pool_info, sizeof(int))) { ret = -5; goto done; }
    if (dev_info != 0) { ret = 2000 + dev_info; goto done; }

    /* Stage the eigenvalues so that h_W is only written once everything has succeeded */
    double *w_tmp = (double*)malloc(w_bytes);
    if (!w_tmp) { ret = -6; goto done; }
    if (!D2H(w_tmp, d_pool_W, w_bytes)) { free(w_tmp); ret = -5; goto done; }
    if (mode_v != 0 && !D2H(h_A, d_pool_A, a_bytes)) {
        /* h_A may be partially overwritten: report a hard error, caller must not fall back */
        free(w_tmp); ret = -100; goto done;
    }
    memcpy(h_W, w_tmp, w_bytes);
    free(w_tmp);

done:
    if (ret == 0) {
        st_calls[ST_ZHEGV]++;   /* no FLOP rate reported: divide & conquer count is data dependent */
    } else {
        st_fail[ST_ZHEGV]++;
    }
    st_time[ST_ZHEGV] += wall_time() - t0;
    LEAVE_CUDA_LOCK();
    return ret;
}

/*
 * Double Precision GEMM via cuBLAS (column-major, Fortran semantics)
 */
int cq_cublas_dgemm(int op_a, int op_b, int m, int n, int k,
                    double alpha, const double *h_A, int lda,
                    const double *h_B, int ldb,
                    double beta, double *h_C, int ldc) {
    if (!g_cuda_available || !g_cublas) return -1;
    if (m <= 0 || n <= 0) return 0;

    ENTER_CUDA_LOCK();
    double t0 = wall_time();
    int ret = 0;

    /* Only the last column needs to be read up to its last used row, so the transfer
       size is ld*(cols-1)+rows; this never reads past the end of a tightly sized array. */
    size_t a_rows = (op_a == CUBLAS_OP_N) ? (size_t)m : (size_t)k;
    size_t a_cols = (op_a == CUBLAS_OP_N) ? (size_t)k : (size_t)m;
    size_t b_rows = (op_b == CUBLAS_OP_N) ? (size_t)k : (size_t)n;
    size_t b_cols = (op_b == CUBLAS_OP_N) ? (size_t)n : (size_t)k;

    size_t a_bytes = (a_cols > 0) ? ((size_t)lda * (a_cols - 1) + a_rows) * sizeof(double) : 0;
    size_t b_bytes = (b_cols > 0) ? ((size_t)ldb * (b_cols - 1) + b_rows) * sizeof(double) : 0;
    size_t c_bytes = ((size_t)ldc * (n - 1) + (size_t)m) * sizeof(double);

    if (ensure_device_buffer(&d_pool_A, &d_pool_A_bytes, a_bytes) ||
        ensure_device_buffer(&d_pool_B, &d_pool_B_bytes, b_bytes) ||
        ensure_device_buffer(&d_pool_C, &d_pool_C_bytes, c_bytes)) {
        ret = -2; goto done;
    }

    if ((a_bytes && !H2D(d_pool_A, h_A, a_bytes)) || (b_bytes && !H2D(d_pool_B, h_B, b_bytes))) { ret = -5; goto done; }
    /* C must also be uploaded when ldc > m (gap rows must survive the D2H copy) */
    if ((beta != 0.0 || ldc > m) && !H2D(d_pool_C, h_C, c_bytes)) { ret = -5; goto done; }

    int stat = fn_cublasDgemm(g_cublas, op_a, op_b, m, n, k,
                              &alpha, (const double*)d_pool_A, lda,
                              (const double*)d_pool_B, ldb,
                              &beta, (double*)d_pool_C, ldc);
    if (stat != CUBLAS_STATUS_SUCCESS) { ret = 1000 + stat; goto done; }
    if (!D2H(h_C, d_pool_C, c_bytes)) { ret = -100; goto done; }

done:
    if (ret == 0) {
        st_calls[ST_DGEMM]++;
        st_flops[ST_DGEMM] += 2.0 * (double)m * (double)n * (double)k;
    } else {
        st_fail[ST_DGEMM]++;
    }
    st_time[ST_DGEMM] += wall_time() - t0;
    LEAVE_CUDA_LOCK();
    return ret;
}

/*
 * Complex Double Precision GEMM via cuBLAS
 */
int cq_cublas_zgemm(int op_a, int op_b, int m, int n, int k,
                    const void *alpha, const void *h_A, int lda,
                    const void *h_B, int ldb,
                    const void *beta, void *h_C, int ldc) {
    if (!g_cuda_available || !g_cublas) return -1;
    if (m <= 0 || n <= 0) return 0;

    ENTER_CUDA_LOCK();
    double t0 = wall_time();
    int ret = 0;

    size_t a_rows = (op_a == CUBLAS_OP_N) ? (size_t)m : (size_t)k;
    size_t a_cols = (op_a == CUBLAS_OP_N) ? (size_t)k : (size_t)m;
    size_t b_rows = (op_b == CUBLAS_OP_N) ? (size_t)k : (size_t)n;
    size_t b_cols = (op_b == CUBLAS_OP_N) ? (size_t)n : (size_t)k;

    size_t a_bytes = (a_cols > 0) ? ((size_t)lda * (a_cols - 1) + a_rows) * sizeof(cq_cplx_t) : 0;
    size_t b_bytes = (b_cols > 0) ? ((size_t)ldb * (b_cols - 1) + b_rows) * sizeof(cq_cplx_t) : 0;
    size_t c_bytes = ((size_t)ldc * (n - 1) + (size_t)m) * sizeof(cq_cplx_t);

    if (ensure_device_buffer(&d_pool_A, &d_pool_A_bytes, a_bytes) ||
        ensure_device_buffer(&d_pool_B, &d_pool_B_bytes, b_bytes) ||
        ensure_device_buffer(&d_pool_C, &d_pool_C_bytes, c_bytes)) {
        ret = -2; goto done;
    }

    if ((a_bytes && !H2D(d_pool_A, h_A, a_bytes)) || (b_bytes && !H2D(d_pool_B, h_B, b_bytes))) { ret = -5; goto done; }

    const double *beta_d = (const double*)beta;
    if ((beta_d[0] != 0.0 || beta_d[1] != 0.0 || ldc > m) && !H2D(d_pool_C, h_C, c_bytes)) { ret = -5; goto done; }

    int stat = fn_cublasZgemm(g_cublas, op_a, op_b, m, n, k,
                              alpha, d_pool_A, lda,
                              d_pool_B, ldb,
                              beta, d_pool_C, ldc);
    if (stat != CUBLAS_STATUS_SUCCESS) { ret = 1000 + stat; goto done; }
    if (!D2H(h_C, d_pool_C, c_bytes)) { ret = -100; goto done; }

done:
    if (ret == 0) {
        st_calls[ST_ZGEMM]++;
        st_flops[ST_ZGEMM] += 8.0 * (double)m * (double)n * (double)k;
    } else {
        st_fail[ST_ZGEMM]++;
    }
    st_time[ST_ZGEMM] += wall_time() - t0;
    LEAVE_CUDA_LOCK();
    return ret;
}

/*
 * 3D Complex-to-Complex FFT via cuFFT, in place, unnormalised (same as FFTW)
 * Data is a Fortran array cdata(nx,ny,nz) (x fastest).
 * isign == -1: Forward transform
 * isign == +1: Inverse transform
 */
int cq_cufft_3d_z2z(int nx, int ny, int nz, void *h_data, int isign) {
    if (!g_cuda_available || !fn_cufftExecZ2Z) return -1;
    if (nx <= 0 || ny <= 0 || nz <= 0) return 0;

    ENTER_CUDA_LOCK();
    double t0 = wall_time();
    int ret = 0;

    if (!g_have_fft_plan || g_cached_fft_nx != nx || g_cached_fft_ny != ny || g_cached_fft_nz != nz) {
        if (g_have_fft_plan) {
            fn_cufftDestroy(g_cached_fft_plan);
            g_have_fft_plan = 0;
        }
        /* cuFFT takes C (row-major) dimensions: slowest first */
        if (fn_cufftPlan3d(&g_cached_fft_plan, nz, ny, nx, CUFFT_Z2Z) != CUFFT_SUCCESS) {
            ret = -2; goto done;
        }
        g_have_fft_plan = 1;
        g_cached_fft_nx = nx;
        g_cached_fft_ny = ny;
        g_cached_fft_nz = nz;
    }

    size_t data_bytes = (size_t)nx * ny * nz * sizeof(cq_cplx_t);

    if (ensure_device_buffer(&d_pool_A, &d_pool_A_bytes, data_bytes)) { ret = -3; goto done; }
    if (!H2D(d_pool_A, h_data, data_bytes)) { ret = -5; goto done; }

    int dir = (isign < 0) ? CUFFT_FORWARD : CUFFT_INVERSE;
    int stat = fn_cufftExecZ2Z(g_cached_fft_plan, d_pool_A, d_pool_A, dir);
    if (stat != CUFFT_SUCCESS) { ret = 1000 + stat; goto done; }
    if (!D2H(h_data, d_pool_A, data_bytes)) { ret = -100; goto done; }

done:
    if (ret == 0) {
        double npts = (double)nx * ny * nz;
        st_calls[ST_FFT]++;
        st_flops[ST_FFT] += 5.0 * npts * log2(npts);
    } else {
        st_fail[ST_FFT]++;
    }
    st_time[ST_FFT] += wall_time() - t0;
    LEAVE_CUDA_LOCK();
    return ret;
}
