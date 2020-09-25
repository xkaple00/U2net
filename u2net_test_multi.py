import os
from skimage import io, transform
import torch
import torchvision
from torch.autograd import Variable
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms#, utils
# import torch.optim as optim

import numpy as np
from PIL import Image
import glob
import cv2

from data_loader import RescaleT
from data_loader import ToTensor
from data_loader import ToTensorLab
from data_loader import SalObjDataset
from data_loader import Augment_prior
from data_loader import ColorJitter



from model import U2NET # full size version 173.6 MB
from model import U2NETP # small version u2net 4.7 MB

# normalize the predicted SOD probability map
def normPRED(d):
    ma = torch.max(d)
    mi = torch.min(d)

    dn = (d-mi)/(ma-mi)

    return dn

# def save_output(image_name,pred,d_dir):

#     predict = pred
#     predict = predict.squeeze()
#     predict_np = predict.cpu().data.numpy()

#     im = Image.fromarray(predict_np*255).convert('RGB')
#     img_name = image_name.split(os.sep)[-1]
#     image = io.imread(image_name)
#     imo = im.resize((image.shape[1],image.shape[0]),resample=Image.BILINEAR)

#     pb_np = np.array(imo)

#     aaa = img_name.split(".")
#     bbb = aaa[0:-1]
#     imidx = bbb[0]
#     for i in range(1,len(bbb)):
#         imidx = imidx + "." + bbb[i]

#     imo.save(d_dir+imidx+'.png')

def main():
    # filename_list = glob.glob('/home/xkaple00/JUPYTER_SHARED/Digis/Background_removal/U-2-Net/train_data/FINAL3_combined')
    # --------- 1. get image path and name ---------
    model_name='u2netp'#u2netp
    # model_dir = os.path.join('/home/xkaple00/JUPYTER_SHARED/Digis/Background_removal/U-2-Net/saved_models/u2netp/166000_train_0.3457.pth')    model_dir = os.path.join('/home/xkaple00/JUPYTER_SHARED/Digis/Background_removal/U-2-Net/saved_models/u2netp/166000_train_0.3457.pth')
    # model_dir = os.path.join('/home/xkaple00/JUPYTER_SHARED/Digis/Background_removal/U-2-Net/saved_models/u2netp/prior_0.5_affine_0.05_loss_0.4585.pth')

    model_dir = os.path.join('/home/xkaple00/JUPYTER_SHARED/Digis/Background_removal/U-2-Net/saved_models/u2netp/itr_8000_train_0.273093_tar_0.022038.pth')

    # model_dir = os.path.join(os.getcwd(), 'saved_models', model_name, model_name + '.pth')
    # model_dir = os.path.join('/home/xkaple00/JUPYTER_SHARED/Digis/Background_removal/U-2-Net/saved_models/u2netp/u2netp.pth')

    # image_dir = os.path.join(os.getcwd(), 'test_data', 'test_images')
    # image_dir = os.path.join(os.getcwd(), 'test_data', 'test_images_mine', 'IMG_9793')
    image_dir = '/home/xkaple00/JUPYTER_SHARED/Digis/Background_removal/U-2-Net/train_data/FINAL3_combined'
    label_dir = '/home/xkaple00/JUPYTER_SHARED/Digis/Background_removal/U-2-Net/train_data/FINAL3_MATTE'

    # prediction_dir = os.path.join(os.getcwd(), 'test_data', model_name + '_results' + os.sep)
    # prediction_dir = os.path.join(os.getcwd(), 'test_data', model_name + 'FINAL4_MATTE' + os.sep)
    output_dir = 'test_data' + os.sep + 'FINAL4_MATTE_predicted' + os.sep

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    img_name_list = glob.glob(image_dir + os.sep + '*')
    lbl_name_list = glob.glob(label_dir + os.sep + '*')

    print('len(lbl_name_list)', len(lbl_name_list))

    # print(img_name_list)

    # --------- 2. dataloader ---------
    #1. dataloader
    test_salobj_dataset = SalObjDataset(img_name_list = img_name_list,
                                        lbl_name_list = lbl_name_list,
                                        # transform=transforms.Compose([
                                        #                             Augment_prior(0.5),
                                        #                             RescaleT((320, 320)),
                                        #                             ToTensorLab(flag=0)])
                                        # )

                                        transform=transforms.Compose([
                                            Augment_prior(0.5),
                                            RescaleT((320,320)),
                                            # RandomCrop(288), #cause of misalignment of label and input
                                            # ColorJitter(brightness=(0.9,1.1),contrast=(0.9,1.1),saturation=(0.9,1.1),hue=0.1),
                                            ToTensorLab(flag=0)]))

    test_salobj_dataloader = DataLoader(test_salobj_dataset,
                                        batch_size=1,
                                        shuffle=False,
                                        num_workers=1)

    # --------- 3. model define ---------
    if(model_name=='u2net'):
        print("...load U2NET---173.6 MB")
        net = U2NET(4,1)
        net.load_state_dict(torch.load(model_dir))

    elif(model_name=='u2netp'):
        print("...load U2NEP---4.7 MB")
        net = U2NETP(4,1)
        net.load_state_dict(torch.load(model_dir))

    if torch.cuda.is_available():
        net.cuda()
    
    net.eval()

    # net = net.load_state_dict(torch.load(model_dir))

    # --------- 4. inference for each image ---------
    for i_test, data_test in enumerate(test_salobj_dataloader):

        print("inferencing:", img_name_list[i_test].split(os.sep)[-1])

        inputs_test = data_test['image']
        print('inputs_test.shape', inputs_test.shape)
        # height, width = inputs_test.shape[2:]
        inputs_test = inputs_test.type(torch.FloatTensor)

        if torch.cuda.is_available():
            inputs_test = Variable(inputs_test.cuda())
        else:
            inputs_test = Variable(inputs_test)

        d0,d1,d2,d3,d4,d5,d6 = net(inputs_test)

        # normalization
        pred = d0[0,0,:,:] * 255
        pred = pred.cpu().detach().numpy()
        # pred = cv2.resize(pred, (height, width))
        print('pred_shape', pred.shape)

        inputs = inputs_test.cpu().detach().numpy()[0]
        input_image = inputs[:3] * 255

        if inputs.shape[0] == 4:
            prior = inputs[3] * 255
            # print('prior_shape', prior.shape)

        input_image = np.moveaxis(input_image, 0, 2)
        input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)

        # print('inputs_shape', inputs.shape)
        # print('inputs_shape', type(inputs))

        # pred = (d0[0][0] + d1[0][0] + d2[0][0] + d3[0][0] + d4[0][0] + d5[0][0] + d6[0][0]) / 7 * 255
        # pred = normPRED(pred)

        # save_output(img_name_list[i_test],pred,output_dir)

        print('save_path', os.path.join(output_dir, str(i_test)+'.png'))

        cv2.imwrite(os.path.join(output_dir, img_name_list[i_test].split(os.sep)[-1]), pred)

        # cv2.imwrite(os.path.join(output_dir, str(i_test)+'_pred.png'), pred)
        # cv2.imwrite(os.path.join(output_dir, str(i_test)+'_inputs.png'), input_image)
        # if inputs.shape[0] == 4:
        #     cv2.imwrite(os.path.join(output_dir, str(i_test)+'_prior.png'), prior) 

        del d0,d1,d2,d3,d4,d5,d6

if __name__ == "__main__":
    main()