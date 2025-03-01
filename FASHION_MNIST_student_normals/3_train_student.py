import tensorflow as tf
import numpy as np
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "2"

from students import *

import configparser
config = configparser.ConfigParser()
config.read('config.ini')
given_size = config['Params'].getint('student_trainable_params')
normal_digit = config['Params'].getint('normal_digit')
log_teacher_output = config['Params'].getboolean('log_teacher_output')
train_on_anomalies = config['Params'].getboolean('train_on_anomalies')

## USER OPTIONS
BATCH_SIZE = 1
lr = 1e-4
np.random.seed(2)
###

(x_train, y_train_orig), (_, _) = tf.keras.datasets.fashion_mnist.load_data()

## same training data as for teacher, no digits removed
x_train = np.reshape(x_train, (len(x_train), 28, 28, 1))
x_train = x_train.astype('float32') / 255.

## load saved AE recon errors as targets
y_train_aed = np.load('AE_outputs/y_train_aed_teacher_normal_CVPR_%s.npy' % normal_digit)

## log transform of teacher logits
if log_teacher_output:
    f = lambda x: np.log(x+1)
    y_train_aed  = f(y_train_aed)

normal_indices = np.where(y_train_orig == normal_digit)[0]

if train_on_anomalies==True:
    all_digits = [0,1,2,3,4,5,6,7,8,9]
    anomalous_digits = np.setdiff1d(all_digits,[normal_digit])
    anomalous_digits_f = np.random.choice(anomalous_digits, size=5, replace = False)
    a1, a2, a3, a4, a5 = anomalous_digits_f.ravel()
    print(a1,a2,a3,a4, a5)

    anom_indices1 = np.where(y_train_orig == a1)[0]
    anom_indices2 = np.where(y_train_orig == a2)[0]
    anom_indices3 = np.where(y_train_orig == a3)[0]
    anom_indices4 = np.where(y_train_orig == a4)[0]
    anom_indices5 = np.where(y_train_orig == a5)[0]

    anom_indices = np.concatenate((anom_indices1, anom_indices2, anom_indices3, anom_indices4, anom_indices5)).flatten()
    print(anom_indices.shape)
    ## 50/50 normal and anomalous digits for training student
    normals = len(normal_indices)
    np.random.seed(42)
    train_indices = np.append(normal_indices, np.random.choice(anom_indices, size=normals, replace=False))

else:
    train_indices = normal_indices


x_train = x_train[train_indices]
y_train_aed = y_train_aed[train_indices]

if given_size == 425:
    student = student_425()
elif given_size == 295:
    student = student_295()
elif given_size == 216:
    student = student_216()
elif given_size == 555:
    student = student_555()
elif given_size == 150:
    student = student_150()
elif given_size == 84:
    student = student_84()

student.summary()
student_trainableParams = np.sum([np.prod(v.get_shape()) for v in student.trainable_weights])
size = student_trainableParams
print('Number of free parameters: ', student_trainableParams)

y_train = y_train_aed
train_ds_orig = tf.data.Dataset.from_tensor_slices((x_train, y_train))

## split into training and validation sets
l = int(len(x_train)*0.9)
train_ds = train_ds_orig.take(l)
validation_ds = train_ds_orig.skip(l)
print(f"Number of training examples: {len(list(train_ds))}.")
print(f"Number of validation examples: {len(list(validation_ds))}.")

train_ds = train_ds.cache().shuffle(15000, reshuffle_each_iteration=True).batch(BATCH_SIZE)
validation_ds = validation_ds.cache().batch(BATCH_SIZE)

optimizer = tf.keras.optimizers.Adam(learning_rate=lr)
student.compile(optimizer = optimizer, loss = tf.keras.losses.MeanAbsoluteError())

savename =  f"students_CVPR/student_CVPR_{size}_{normal_digit}{'_log' if log_teacher_output else ''}"
mcc = tf.keras.callbacks.ModelCheckpoint(
    filepath=savename,
    save_weights_only=False,
    monitor='val_loss',
    mode='min',
    save_best_only=True)

csv_logger = tf.keras.callbacks.CSVLogger('%s_log' % (savename), append=True, separator=';')
es = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=7)

print('ANOMALOUS:', normal_digit)
history = student.fit(
    train_ds,
    validation_data=validation_ds,
    epochs=50,
    callbacks = [es, csv_logger, mcc]
)