# PhotoCuration

iOS Photos and Camera apps are a full featured photo/video (called assets) editors and allow very easy and advanced asset curation, commenting and organization.
It isn't fair that when extracting curated assets from your phone, you'll get an untagged and boring **IMG_1234.jpg** file.
It isn't fair that only iCloud and Mac users (with Mac Photos app) get the benefits of an organized photo library, having to pay for iCloud storage.

PhotoCuration uses [iOSbackup](https://github.com/avibrazil/iOSbackup) to see all asset curation user did and extracts them tagging and renaming along the way.
Instead of having a collection of boring files named as **IMG_1234.jpg**, PhotoCuration delivers assets as **2020.01.22-08.27.59 ★ Boarding on Orlando airport 【Avi Alkalay·︎iPhone 11 Pro】.jpg**.
Note that filename has date and time, a caption, photo author, device type and even a “★” denoting a liked asset.

All this information is yours and is available into your device's Photo Library database (`CameraRollDomain::Media/PhotoData/Photos.sqlite`) and there is no reason to loose it just because you don't pay iCloud.

PhotoCuration acts not only on filenames but also on EXIF/XMP/IPTC/MPEG-4 tagging and subtitling (videos only), embedding all asset metadata as people faces, taken location etc into each file.
PhotoCuration handles special assets as time lapses and slow motion videos. It applies special lossless transformations and interesting wallclock subtitles.