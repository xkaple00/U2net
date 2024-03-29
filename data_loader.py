# data loader
from __future__ import print_function, division
import glob
import torch
from skimage import io, transform, color
import numpy as np
import random
import math
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, utils
from PIL import Image
import cv2

ratio_return_unchanged = 0.1
ratio_do_transform = 0.02

USE_PRIOR = True

# ===================== generate prior channel for input image =====================
def data_motion_blur(image, mask):
    if random.random()<ratio_return_unchanged:
        return image, mask
    
    degree = random.randint(5, 30)
    angle = random.randint(0, 360)
    
    M = cv2.getRotationMatrix2D((degree/2, degree/2), angle, 1)
    motion_blur_kernel = np.diag(np.ones(degree))
    motion_blur_kernel = cv2.warpAffine(motion_blur_kernel, M, (degree, degree))
    motion_blur_kernel = motion_blur_kernel/degree
    
    img_blurred = cv2.filter2D(image, -1, motion_blur_kernel)
    mask_blurred = cv2.filter2D(mask, -1, motion_blur_kernel)
    
    cv2.normalize(img_blurred, img_blurred, 0, 255, cv2.NORM_MINMAX)
    cv2.normalize(mask_blurred, mask_blurred, 0, 1, cv2.NORM_MINMAX)
    return img_blurred, mask_blurred
    
def data_motion_blur_prior(prior):
    if random.random()<ratio_return_unchanged:
        return prior
    
    degree = random.randint(5, 30)
    angle = random.randint(0, 360)
    
    M = cv2.getRotationMatrix2D((degree/2, degree/2), angle, 1)
    motion_blur_kernel = np.diag(np.ones(degree))
    motion_blur_kernel = cv2.warpAffine(motion_blur_kernel, M, (degree, degree))
    motion_blur_kernel = motion_blur_kernel/degree
    
    prior_blurred = cv2.filter2D(prior, -1, motion_blur_kernel)
    return prior_blurred  
    
def data_Affine(image, mask, height, width, bias, ratio=ratio_do_transform):
    if random.random()<ratio_return_unchanged:
        return image, mask

    pts1 = np.float32([[0+bias[0], 0+bias[1]], [width+bias[2], 0+bias[3]], [0+bias[4], height+bias[5]]])
    pts2 = np.float32([[0+bias[6], 0+bias[7]], [width+bias[8], 0+bias[9]], [0+bias[10], height+bias[11]]])

    M = cv2.getAffineTransform(pts1, pts2)

    img_affine = cv2.warpAffine(image, M, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    mask_affine = cv2.warpAffine(mask, M, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) 

    return img_affine, mask_affine

def data_Affine_prior(prior, height, width, bias, ratio=ratio_do_transform):
    if random.random()<ratio_return_unchanged:
        return prior

    pts1 = np.float32([[0+bias[0], 0+bias[1]], [width+bias[2], 0+bias[3]], [0+bias[4], height+bias[5]]])
    pts2 = np.float32([[0+bias[6], 0+bias[7]], [width+bias[8], 0+bias[9]], [0+bias[10], height+bias[11]]])
    M = cv2.getAffineTransform(pts1, pts2)

    prior_affine = cv2.warpAffine(prior, M, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    return prior_affine
    
def data_Perspective(image, mask, height, width, bias, ratio=ratio_do_transform):
    if random.random()<ratio_return_unchanged:
        return image, mask

    pts1 = np.float32([[0+bias[0],0+bias[1]], [height+bias[2],0+bias[3]], 
                       [0+bias[4],width+bias[5]], [height+bias[6], width+bias[7]]])
    pts2 = np.float32([[0+bias[8],0+bias[9]], [height+bias[10],0+bias[11]], 
                       [0+bias[12],width+bias[13]], [height+bias[14], width+bias[15]]])
    M = cv2.getPerspectiveTransform(pts1, pts2)

    img_perspective = cv2.warpPerspective(image, M, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    mask_perspective = cv2.warpPerspective(mask, M, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    return img_perspective, mask_perspective

def data_Perspective_prior(prior, height, width, bias, ratio=ratio_do_transform):
    if random.random()<ratio_return_unchanged:
        return prior

    pts1 = np.float32([[0+bias[0],0+bias[1]], [height+bias[2],0+bias[3]], 
                       [0+bias[4],width+bias[5]], [height+bias[6], width+bias[7]]])
    pts2 = np.float32([[0+bias[8],0+bias[9]], [height+bias[10],0+bias[11]], 
                       [0+bias[12],width+bias[13]], [height+bias[14], width+bias[15]]])
    M = cv2.getPerspectiveTransform(pts1, pts2)

    prior_perspective = cv2.warpPerspective(prior, M, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    return prior_perspective

def data_ThinPlateSpline(image, mask, height, width, ratio=ratio_do_transform):
    if random.random()<ratio_return_unchanged:
        return image, mask
    bias = np.random.randint(-int(height*ratio),int(width*ratio), 16)

    tps = cv2.createThinPlateSplineShapeTransformer()
    sshape = np.array([[0+bias[0],0+bias[1]], [height+bias[2],0+bias[3]], 
                       [0+bias[4],width+bias[5]], [height+bias[6], width+bias[7]]], np.float32)
    tshape = np.array([[0+bias[8],0+bias[9]], [height+bias[10],0+bias[11]], 
                       [0+bias[12],width+bias[13]], [height+bias[14], width+bias[15]]], np.float32)
    sshape = sshape.reshape(1,-1,2)
    tshape = tshape.reshape(1,-1,2)
    matches = list()
    matches.append(cv2.DMatch(0,0,0))
    matches.append(cv2.DMatch(1,1,0))
    matches.append(cv2.DMatch(2,2,0))
    matches.append(cv2.DMatch(3,3,0))
    
    tps.estimateTransformation(tshape, sshape, matches)
    res = tps.warpImage(image)
    res_mask = tps.warpImage(mask)
    return res, res_mask   

def data_ThinPlateSpline_prior(prior, height, width, ratio=ratio_do_transform):
    if random.random()<ratio_return_unchanged:
        return prior
    bias = np.random.randint(-int(height*ratio),int(width*ratio), 16)

    tps = cv2.createThinPlateSplineShapeTransformer()
    sshape = np.array([[0+bias[0],0+bias[1]], [height+bias[2],0+bias[3]], 
                       [0+bias[4],width+bias[5]], [height+bias[6], width+bias[7]]], np.float32)
    tshape = np.array([[0+bias[8],0+bias[9]], [height+bias[10],0+bias[11]], 
                       [0+bias[12],width+bias[13]], [height+bias[14], width+bias[15]]], np.float32)
    sshape = sshape.reshape(1,-1,2)
    tshape = tshape.reshape(1,-1,2)
    matches = list()
    matches.append(cv2.DMatch(0,0,0))
    matches.append(cv2.DMatch(1,1,0))
    matches.append(cv2.DMatch(2,2,0))
    matches.append(cv2.DMatch(3,3,0))
    
    tps.estimateTransformation(tshape, sshape, matches)
    prior = tps.warpImage(prior)
    return prior

class Augment_prior(object):

	def __init__(self, prior_prob):

		self.prior_prob = prior_prob

	def __call__(self,sample):
		imidx, image, label, prior = sample['imidx'], sample['image'],sample['label'], sample['prior']

		h, w = image.shape[:2]
		height, width = label.shape[:2]

		image_array = image.astype(np.uint8)

		label_array = label.astype(np.uint8)

		image = Image.fromarray(image.astype(np.uint8))
		prior_array = np.zeros((height, width, 1))

		if self.prior_prob >= random.random(): # probability to distore prior
			
			prior_array = prior.astype(np.uint8)
			prior = Image.fromarray((prior[:,:,0]).astype(np.uint8))

			image_label_array = np.concatenate((image_array, label_array), axis=-1)
			image_label = Image.fromarray(image_label_array.astype(np.uint8))

			if random.random() > 1.: #!!! discard if >1

				image_label = transforms.RandomAffine(degrees=1, translate=(0.01, 0.01), scale=None, shear=(1, 1, 1, 1), resample=False, fillcolor=0)(image_label)
				
				image_label_array = np.array(image_label)
				image_array = image_label_array[:,:,:3]
				label_array = image_label_array[:,:,3:]

			else:
				# modify prior, don't change image + mask
				prior = transforms.RandomAffine(degrees=1, translate=(0.01, 0.01), scale=None, shear=(2, 2, 2, 2), resample=False, fillcolor=0)(prior)
				# prior = transforms.RandomAffine(degrees=0, translate=(0.0, 0.0), scale=None, shear=(0.,0.,0.,0.), resample=False, fillcolor=0)(prior)

				prior_array = np.array(prior)
				prior_array = prior_array[:,:,np.newaxis]

		return {'imidx':imidx, 'image':image_array,'label':label_array, 'prior':prior_array}

class ColorJitter(object):

	def __init__(self,brightness,contrast,saturation,hue):

		self.brightness = brightness
		self.contrast = contrast
		self.saturation = saturation
		self.hue = hue

	def __call__(self,sample):
		imidx, image, label, prior = sample['imidx'], sample['image'],sample['label'],sample['prior']

		image = Image.fromarray(np.uint8(image))

		image = transforms.ColorJitter(brightness=self.brightness, contrast=self.contrast, saturation=self.saturation, hue=self.hue)(image)
		image = np.array(image) 

		return {'imidx':imidx, 'image':image,'label':label, 'prior':prior}

class RescaleT(object):

	def __init__(self,output_size):
		assert isinstance(output_size,(int,tuple))
		self.output_size = output_size

	def __call__(self,sample):
		imidx, image, label, prior = sample['imidx'], sample['image'],sample['label'], sample['prior']

		image = Image.fromarray(np.uint8(image))
		
		prior = Image.fromarray(np.uint8(prior[:,:,0]))
		label = Image.fromarray(np.uint8(label[:,:,0]))

		image = transforms.Resize(self.output_size, interpolation=2)(image)
		prior = transforms.Resize(self.output_size, interpolation=2)(prior)
		label = transforms.Resize(self.output_size, interpolation=2)(label)

		image = np.array(image)

		prior = np.array(prior)
		prior = prior[:,:,np.newaxis]
		label = np.array(label)
		label = label[:,:,np.newaxis]

		return {'imidx':imidx, 'image':image,'label':label, 'prior':prior}

class RandomCrop(object):

	def __init__(self,output_size):
		assert isinstance(output_size, (int, tuple))
		if isinstance(output_size, int):
			self.output_size = (output_size, output_size)
		else:
			assert len(output_size) == 2
			self.output_size = output_size
	def __call__(self,sample):
		imidx, image, label = sample['imidx'], sample['image'], sample['label']

		prior = image[:,:,3:]
		image = image[:,:,:3]

		image = Image.fromarray(np.uint8(image))
		prior = Image.fromarray(np.uint8(prior[:,:,0]))
		label = Image.fromarray(np.uint8(label[:,:,0]))

		image = transforms.RandomCrop(self.output_size)(image)
		prior = transforms.RandomCrop(self.output_size)(prior)
		label = transforms.RandomCrop(self.output_size)(label)

		image = np.array(image)
		prior = np.array(prior)
		prior = prior[:,:,np.newaxis]
		label = np.array(label)
		label = label[:,:,np.newaxis]

		image = np.concatenate((image, prior), axis=-1)

		return {'imidx':imidx,'image':image, 'label':label}

class ToTensor(object):
	"""Convert ndarrays in sample to Tensors."""

	def __call__(self, sample):

		imidx, image, label = sample['imidx'], sample['image'], sample['label']

		tmpImg = np.zeros((image.shape[0],image.shape[1],3))
		tmpLbl = np.zeros(label.shape)

		image = image/np.max(image)
		if(np.max(label)<1e-6):
			label = label
		else:
			label = label/np.max(label)

		if image.shape[2]==1:
			tmpImg[:,:,0] = (image[:,:,0]-0.485)/0.229
			tmpImg[:,:,1] = (image[:,:,0]-0.485)/0.229
			tmpImg[:,:,2] = (image[:,:,0]-0.485)/0.229
		else:
			tmpImg[:,:,0] = (image[:,:,0]-0.485)/0.229
			tmpImg[:,:,1] = (image[:,:,1]-0.456)/0.224
			tmpImg[:,:,2] = (image[:,:,2]-0.406)/0.225

		tmpLbl[:,:,0] = label[:,:,0]

		tmpImg = tmpImg.transpose((2, 0, 1))
		tmpLbl = label.transpose((2, 0, 1))

		return {'imidx':torch.from_numpy(imidx), 'image': torch.from_numpy(tmpImg), 'label': torch.from_numpy(tmpLbl)}

class ToTensorLab(object):
	"""Convert ndarrays in sample to Tensors."""
	def __init__(self,flag=0):
		self.flag = flag

	def __call__(self, sample):

		imidx, image, label, prior = sample['imidx'], sample['image'], sample['label'], sample['prior']

		tmpLbl = np.zeros(label.shape)

		if(np.max(label)<1e-6):
			label = label
		else:
			label = label/np.max(label)

		if(np.max(prior)<1e-6):
			prior = prior
		else:
			prior = prior/np.max(prior)

		tmpImg = np.zeros((image.shape[0],image.shape[1],4))

		image = image/255

		if image.shape[2]==1:
			tmpImg[:,:,0] = image[:,:,0]
			tmpImg[:,:,1] = image[:,:,0]
			tmpImg[:,:,2] = image[:,:,0]
			tmpImg[:,:,3] = prior[:,:,0]
		else:
			tmpImg[:,:,0] = image[:,:,0]
			tmpImg[:,:,1] = image[:,:,1]
			tmpImg[:,:,2] = image[:,:,2]
			tmpImg[:,:,3] = prior[:,:,0]
			
		tmpLbl[:,:,0] = label[:,:,0]

		tmpImg = np.moveaxis(tmpImg, 2, 0)
		tmpLbl = np.moveaxis(tmpLbl, 2, 0)

		return {'imidx':torch.from_numpy(imidx), 'image': torch.from_numpy(tmpImg), 'label': torch.from_numpy(tmpLbl)}


class SalObjDataset(Dataset):
	def __init__(self, img_name_list, lbl_name_list, pri_name_list, transform=None):

		self.image_name_list = sorted(img_name_list)
		self.label_name_list = sorted(lbl_name_list)
		self.prior_name_list = sorted(pri_name_list)

		self.transform = transform

	def __len__(self):
		return len(self.image_name_list)

	def __getitem__(self,idx):

		image = io.imread(self.image_name_list[idx])
		imname = self.image_name_list[idx]
		imidx = np.array([idx])

		if(0==len(self.label_name_list)):
			label_3 = np.zeros(image.shape)
		else:
			label_3 = io.imread(self.label_name_list[idx])

		if(0==len(self.prior_name_list)):
			prior_3 = np.zeros(image.shape)
		else:
			prior_3 = io.imread(self.prior_name_list[idx])

		label = np.zeros(label_3.shape[0:2])
		if(3==len(label_3.shape)):
			label = label_3[:,:,0]
		elif(2==len(label_3.shape)):
			label = label_3

		prior = np.zeros(prior_3.shape[0:2])
		if(3==len(prior_3.shape)):
			prior = prior_3[:,:,0]
		elif(2==len(prior_3.shape)):
			prior = prior_3

		if(3==len(image.shape) and 2==len(label.shape)):
			label = label[:,:,np.newaxis]
		elif(2==len(image.shape) and 2==len(label.shape)):
			image = image[:,:,np.newaxis]
			label = label[:,:,np.newaxis]

		if(3==len(image.shape) and 2==len(prior.shape)):
			prior = prior[:,:,np.newaxis]
		elif(2==len(image.shape) and 2==len(prior.shape)):
			image = image[:,:,np.newaxis]
			prior = prior[:,:,np.newaxis]

		sample = {'imidx':imidx, 'image':image, 'label':label, 'prior':prior}

		if self.transform:
			sample = self.transform(sample)

		return sample
