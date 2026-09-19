// Full CSR matvec on macOS GCD. Every row and edge participates, in stored order.
// No fast-math, connectivity pruning, event approximation, or neuron subsampling.
#include <dispatch/dispatch.h>
#include <stdint.h>
#include <stddef.h>
typedef struct {const int32_t *ptr,*col;const float *val,*x;float *out;size_t n,tasks;} Matrix;
static void row_block(void *context,size_t block){
 Matrix *m=context;size_t lo=block*m->n/m->tasks,hi=(block+1)*m->n/m->tasks;
 for(size_t i=lo;i<hi;i++){float sum=0;for(int32_t j=m->ptr[i];j<m->ptr[i+1];j++)sum+=m->val[j]*m->x[m->col[j]];m->out[i]=sum;}
}
void csr_matvec(const int32_t *ptr,const int32_t *col,const float *val,const float *x,float *out,size_t n,size_t tasks){
 Matrix m={ptr,col,val,x,out,n,tasks};dispatch_apply_f(tasks,dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),&m,row_block);
}
