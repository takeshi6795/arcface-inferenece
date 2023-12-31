from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
import argparse
#import tensorflow as tf
import numpy as np
import mxnet as mx
import random
import cv2
#import sklearn
#from sklearn.decomposition import PCA
from time import sleep
from mtcnn_detector import MtcnnDetector
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'common'))
#import face_image
import face_preprocess


def do_flip(data):
  for idx in range(data.shape[0]):
    data[idx,:,:] = np.fliplr(data[idx,:,:])

def get_model(ctx, image_size, model_str, layer):
  _vec = model_str.split(',')
  assert len(_vec)==2
  prefix = _vec[0]
  epoch = int(_vec[1])
  print('loading',prefix, epoch)
  sym, arg_params, aux_params = mx.model.load_checkpoint(prefix, epoch)
  all_layers = sym.get_internals()
  sym = all_layers[layer+'_output']
  model = mx.mod.Module(symbol=sym, context=ctx, label_names = None)
  #model.bind(data_shapes=[('data', (args.batch_size, 3, image_size[0], image_size[1]))], label_shapes=[('softmax_label', (args.batch_size,))])
  model.bind(data_shapes=[('data', (1, 3, image_size[0], image_size[1]))])
  model.set_params(arg_params, aux_params)
  return model

class FaceModel:
  def __init__(self, args):
    self.args = args
    ctx = mx.gpu(args.gpu)
    #ctx = mx.cpu()
    _vec = args.image_size.split(',')
    assert len(_vec)==2
    image_size = (int(_vec[0]), int(_vec[1]))
    self.model = None
    self.ga_model = None
    if len(args.model)>0:
      self.model = get_model(ctx, image_size, args.model, 'fc1')
    if len(args.ga_model)>0:
      self.ga_model = get_model(ctx, image_size, args.ga_model, 'fc1')

    self.threshold = args.threshold
    self.det_minsize = 20
    #self.det_threshold = [0.6,0.7,0.9]
    self.det_threshold = [0.6,0.7,0.8]
    self.det_factor = 0.85
    self.image_size = image_size
    mtcnn_path = os.path.join(os.path.dirname(__file__), 'mtcnn-model')
    if args.det==0:
      detector = MtcnnDetector(model_folder=mtcnn_path, ctx=ctx, num_worker=1, accurate_landmark = True, threshold=self.det_threshold)
      #detector = MtcnnDetector(model_folder=mtcnn_path, ctx=ctx, num_worker=1, minsize=self.det_minsize, factor=self.det_factor, accurate_landmark = True, threshold=self.det_threshold )
    else:
      detector = MtcnnDetector(model_folder=mtcnn_path, ctx=ctx, num_worker=1, accurate_landmark = True, threshold=[0.0,0.0,0.2])
    self.detector = detector


  def get_input(self, face_img):
    ret = self.detector.detect_face(face_img, det_type = self.args.det)
    if ret is None:
      return None
    bbox, points = ret
    if bbox.shape[0]==0:
      return None

    #bbox = bbox[0,0:4]
    #points = points[0,:].reshape((2,5)).T

    nrof_faces = bbox.shape[0]
    det = bbox[:,0:4]
    img_size = np.asarray(face_img.shape)[0:2]
    bindex = 0
    if nrof_faces>1:
        bounding_box_size = (det[:,2]-det[:,0])*(det[:,3]-det[:,1])
        img_center = img_size / 2
        offsets = np.vstack([ (det[:,0]+det[:,2])/2-img_center[1], (det[:,1]+det[:,3])/2-img_center[0] ])
        offset_dist_squared = np.sum(np.power(offsets,2.0),0)
        bindex = np.argmax(bounding_box_size-offset_dist_squared*2.0) # some extra weight on the centering
    _bbox = bbox[bindex, 0:4]
    _landmark = points[bindex, :].reshape( (2,5) ).T
    nimg = face_preprocess.preprocess(face_img, bbox=_bbox, landmark = _landmark, image_size='112,112')
    #nimg = face_preprocess.preprocess(face_img, bbox, points, image_size='112,112')
    nimg = cv2.cvtColor(nimg, cv2.COLOR_BGR2RGB)
    aligned = np.transpose(nimg, (2,0,1))
    return aligned, _bbox

  def get_feature(self, aligned):
    input_blob = np.expand_dims(aligned, axis=0)
    data = mx.nd.array(input_blob)
    db = mx.io.DataBatch(data=(data,))
    self.model.forward(db, is_train=False)
    embedding = self.model.get_outputs()[0].asnumpy()
    embedding = embedding / np.linalg.norm(embedding)
    return embedding

  def get_ga(self, aligned):
    input_blob = np.expand_dims(aligned, axis=0)
    data = mx.nd.array(input_blob)
    db = mx.io.DataBatch(data=(data,))
    self.ga_model.forward(db, is_train=False)
    ret = self.ga_model.get_outputs()[0].asnumpy()
    g = ret[:,0:2].flatten()
    gender = np.argmax(g)
    a = ret[:,2:202].reshape( (100,2) )
    a = np.argmax(a, axis=1)
    age = int(sum(a))

    return gender, age

