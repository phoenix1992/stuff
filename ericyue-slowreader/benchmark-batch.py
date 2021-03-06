# measure the speed at which batches can be made
# Only 14k 
# range queue 1996115, batch queue 3885, 6455.13 per second
# range d 404771, batch d 3229
# range queue 1988698, batch queue 11302, 14735.80 per second
# range d -7417, batch d 7417
# range queue 1981384, batch queue 18616, 14620.57 per second
# range d -7314, batch d 7314
# range queue 1974016, batch queue 25984, 14662.89 per second

import tensorflow as tf
import time


steps_to_validate = 200
epoch_number = 2
thread_number = 2
batch_size = 100

capacity = 2*10**6
# don't use too high of limit, 10**9 hangs (overflows to negative in TF?)
a_queue = tf.train.range_input_producer(limit=10**3, num_epochs=2000,
                                        capacity=capacity, shuffle=False)

# manually run the queue runner for a bit
config = tf.ConfigProto(log_device_placement=False)
config.operation_timeout_in_ms=5000   # terminate on long hangs
sess = tf.InteractiveSession("", config=config)
sess.run(tf.global_variables_initializer())
sess.run(tf.local_variables_initializer())


a_queue_qr = tf.get_collection(tf.GraphKeys.QUEUE_RUNNERS)[0]
for i in range(1000):
    sess.run(a_queue_qr.enqueue_ops)


# check the size
range_size_node = "input_producer/fraction_of_2000000_full/fraction_of_2000000_full_Size:0"

# size gives raw size rather than number of batches
batch_size_node = "batch/fifo_queue_Size:0"

print("range size is ", sess.run(range_size_node))

# now create batch and run it manually
# use size of 2 or get TypeError: 'Tensor' object is not iterable.
# (possibly singleton list get auto-packed into a single Tensor)
[b, _] = tf.train.batch([a_queue.dequeue()]*2, batch_size=batch_size,
                        capacity=capacity)


tf.train.start_queue_runners()
start_time = time.time()
old_range_size, old_batch_size = (0, 0)
while True:
    new_range_size, new_batch_size = sess.run([range_size_node, batch_size_node])
    
    new_time = time.time()
    rate = (new_batch_size-old_batch_size)/(new_time-start_time)
    print("range queue %d, batch queue %d, %.2f per second"%(new_range_size,
                                                             new_batch_size,
                                                             rate))
    print("range d %d, batch d %d" %(new_range_size - old_range_size,
                                     new_batch_size - old_batch_size))
    start_time = time.time()
    old_range_size, old_batch_size = new_range_size, new_batch_size 
    time.sleep(0.5)



def let_queue_repopulate(size_tensor, min_elements=100000, sleep_delay=0.5):
    """Wait until queue has enough elements."""
    size2 = "input_producer/fraction_of_2000000_full/fraction_of_2000000_full_Size:0"
    while sess.run(size_tensor) < min_elements:
        print("Size1: %d, size2: %d" %tuple(sess.run([size_tensor, size2])))
        time.sleep(sleep_delay)

step = 0
start_time = time.time()
while True:
    step+=1
    let_queue_repopulate(size_tensor=batch_size_node)
    sess.run(b.op)
    if step % steps_to_validate == 0:
        end_time = time.time()
        sec = (end_time - start_time)
        print("[{}] time[{:6.2f}] step[{:10d}] speed[{:6d}]".format(
            str(end_time).split(".")[0],sec, step,
            int((steps_to_validate*batch_size)/sec)
        ))
        start_time = end_time
