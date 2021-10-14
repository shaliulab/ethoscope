[![Documentation Status](https://readthedocs.org/projects/ethoscope/badge/?version=latest)](http://ethoscope.readthedocs.org/en/latest/?badge=latest)
[![Documentation Status](https://readthedocs.org/projects/ethoscope/badge/?version=dev)](http://ethoscope.readthedocs.org/en/dev/?badge=dev)
Ethoscope
============

This is the github repository of the software part of the [ethoscope platform](http://gilestrolab.github.io/ethoscope/).
All technical information regarding ethoscope is compiled in [our documentation](https://qgeissmann.gitbooks.io/ethoscope-manual/content/).


Organisation of the branches
--------------------------------

* `deployment`: base branch running on the ethoscopes in the lab
* `deployment_sd`: fork of deployment with advanced interactor classes
* `super_ethoscope`: fork of deployment with advanced tracking and camera classes:
*    The RichAdaptiveBGTracker provides total movement correlates of activity
*    The ImgStoreCamera allows the ethoscope platform to read from the imgstore format
*    The HRPiCameraAsync allows the ethoscope to take HQ images (4k x 3k) and saves them to an imgstore. The FPS is reduced (~0.25 FPS vs ~2 FPS).





Organisation of the code
--------------------------

* `src` contains the main python package named `ethoscope`. It is installed on video monitors (devices), but it can be used as a standalone off-line tracking tool.
* `node-src` contains the software stack running on the 'node'. Node is a unique computer that syncs and controls devices.
* `prototypes` contains (often unsuccessful) developmental trials.
* `scripts` contains a toolbox of scripts. For instance to install the software on target device or to convert aquiered videos to a handy format.


Branching system
--------------------------

* `master` is **only** used for hosting tested **stable** software.
* `dev` is a fairly stable developmental used in @gilestrolab.

The workflow is to make issue branches from `dev`, test them as much a possible before merging them to `dev`.
Then, we deploy them in `dev`, and update all devices in the @gilestrolab.
If we experience no new critical issues over several weeks, we can merge `dev` to `master`, allowing the rest of the world to upgrade.

License
---------------

Ethoscope source code is licensed under the **GPL3** (see [license file](LICENSE)).

Run offline
------------

From the `./src/ethoscope/scripts` folder run:

```
python device_server.py --rois-pickle-file PATH_TO_ROIS.pickle --input PATH_TO_VIDEO.mp4 --use-wall-clock --drop-each 1 --tracker RichAdaptiveBGModel --camera FSLVirtualCamera --name FLYSLEEPLAB_CV1 --address 192.169.123.10
```
*rois pickle file: A pickle file storing a list of instances of the ROI class. This is the output of the ROI builder algorithm executed upon start of the recording. If not provided, the software attempts to finding the ROIs from the video. Convenient because it allows for running the ROI builder algorithm at recording time, so issues can be fixed live.

* use wall clock: will use the time of the video as reference for the analysis. This means t will be mapped to the time of the frame, and not the real time of the offline analysis. So for a video at 10 FPS, the third frame has time 0.3, no matter how long it takes to analyze the first two frames.

* drop each: If not 1, it will drop every drop-each frame. Example: 2 will drop half the frames, 3 one third, etc. Useful for downsampling.

* tracker: Name of the tracking class
* name: Name of the offline ethoscope as displayed in the ethoscope node GUI
* address: This argument is mandatory for now if you want to see the offline ethoscope appear on the GUI. This is because the code in charge of fetching the ip address of the ethoscopes does not work when running offline. With this argument the user can avert this issue.
 

