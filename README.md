# PhotoCuration

iOS Photos and Camera apps are a full featured photo/video (called assets) editors and allow very easy and advanced asset curation, commenting and organization.
It isn't fair that when extracting curated assets from your phone, you'll get an untagged and boring **IMG_1234.jpg** file.
It isn't fair that only iCloud and Mac users (with Mac Photos app) get the benefits of an organized photo library, having to pay for iCloud storage.

PhotoCuration uses [iOSbackup](https://github.com/avibrazil/iOSbackup) to see all asset curation user did and extracts them tagging and renaming along the way.
Instead of having a collection of boring files named as **IMG_1234.jpg**, PhotoCuration delivers assets as **2020.01.22-08.27.59 ★ Boarding at Orlando airport 【Avi Alkalay·︎iPhone 11 Pro】.jpg**.
Note that filename has date and time, a caption, photo author, device type and even a “★” denoting a liked asset.

All this information is yours and is available into your device's Photo Library database (`CameraRollDomain::Media/PhotoData/Photos.sqlite`) and there is no reason to loose it just because you don't pay iCloud.

PhotoCuration acts not only on filenames but also on EXIF/XMP/IPTC/MPEG-4 tagging and subtitling (videos only), embedding all asset metadata as people faces, taken location etc into each file.
PhotoCuration handles special assets as time lapses and slow motion videos. It applies special lossless transformations and interesting wallclock subtitles.

## Photo and Media management workflow

iOS devices have powerful and complete photo editing tools. Not only in the visuals and color level, but also provides amazing tools
to organize your photos and videos. All of that translates into data stored in an in-device database.

PhotoCuration job is to use all this information to properly extract, archive, organize, rename and tag your media (photos and videos).

### Workflow for each photo and video

1. Tag recognized faces with person's names. Use iOS tools to merge and remove duplicate persons
1. Fix and improve color, position, zoom, depth and rotation
    1. Edit the media
    1. Use **Auto** tool under **Adjust** filters
    1. Select some color improvement filters under **Filters**
    1. Try **Portrait** light simulation filters, as **Studio Light** or **Countour Light**
    1. Manipulate **Portrait**’s **Depth** to allow subject to pop from photo
    1. Use **Crop and Rotation** tools to crop, rotate, straighten the photo or video
    1. Spend some time to understand the power of all these photo editing tools, don’t be affraid of messing up, because...
    1. ...You can always revert to original and start over
1. Mark best photos and videos with a ♥︎
1. Slide photo up and:
    1. Write a caption as “Clara plays with a dog on the beach”; do this for each and every photo. Use emoji and unicode, be creative but avoid multiple lines
    1. Usually unneccessary: adjust media date, time and location taken (photos taken with iOS always have correct time and location)
1. Video only: clip start and end of the video
    1. Avoid doing that because it will make impossible to find correct video recording time
    1. Prefer doing such clips later in a computer, after PhotoCuration has extracted and tagged them
1. Slow motion videos: use the tool to make slow only the most important part of the media
    1. This tool only affect video playback, doesn't change the original video
    1. Slow motion videos are simple high frame rate videos. PhotoCuration will extract 2 versions of these types: the original high frame rate video, and an entirely slow motion video losslesslly manipulating only the framerate of the MPEG-4 file.
1. Burst of photos:
    1. Under **Albums**, select **Bursts** and for each burst:
        1. Use **Select...** to select only the best photos of the burst
        1. Hit **Done** and select **Keep Only N Favorites** to separate the burst and delete undesired photos
1. Live photos:
    1. Use the upper left tool to turn them into a Loop, Bounce or Long Exposure
    1. This only changes the playback, not the unrelying media
    1. Live photos are physically just small videos; PhotoCuration will extract the video and an associated photo created by iOS

### Organize Photos

All the above will help you organize photos in albums and make beautiful short videos of events

1. Select all media related to an event, party, trip, people encounter, season or anything that comes to your mind
1. Use the **Share** button and select **Add to Album**
1. Give a nice name to the album, such as “Beach weekend with cousins” or “Avi’s birthday party” or “Spring blossoms”. You can always rename albums and add more media to each
    1. Use emoji and unicode, be creative
1. Use same method to add more media to an existing album. Or use the in-album “✚” to add media to it
1. You can put same photo/video in multiple albums
1. Under **Albums**, you can also create **Folders** and put other albums inside of them. iOS won’t allow you to move existing albums into another folder, though, you'll have to re-create the album inside a folder and re-insert media into new album.

While extracting, PhotoCuration will create nicelly named folders in the filesystem for each album that contains photos

### Make short and summary videos of your Albums using **Photos Memories**

iOS Photos has the amazing **Memories** feature. Use it like this:

1. Enter an album you’ve just created as above, on the top right menu select **Play Memory Video**
1. iOS will use curation actions you have taken to dice what to show in this video, but you can improve it even more
1. While playing, select **Manage Photos** on top right menu, then **Deselect All** media and select only the ones you marked with ♥︎
1. Select a differente background audio under **♫**. I prefer the **Categories** under **Sountracks**, using some instrumental song
    1. If you don’t change the music, you probably won't be able to export the Memory as a regular video
    1. Tap **Memory Mixes** on the top to exit music selection and return to the video
1. Change Memory title and subtitle. This is the text that appears in the begining of video. Use emoji an unicode, be creative
1. Use **Share** button on the top to export it to a regular video in you camera roll
1. Use the **Options** on the top of sharing pane to select orientation and aspect ratio. I always prefer **Landscape** and **16:9**, to make it look nice on a TV
    1. iOS will create an MPEG-4 video file, save in your camera roll and make the video independent from Memories tool    
1. Go back to the Album that generated this video and use “✚” to add it to the album
1. Correctly adjust video’s meta information
    1. Adjust time and date to the end of the event. So if last event original photo is 10:30, adjust video’s to 10:35 on the same date
    1. Adjust video location
    1. Write a caption for the video, as “Summary for Weekend on the Beach”

### Make short and summary videos of your Albums using **iOS iMovie**

If you are not happy with the video created by Photos Memories, you can use **iOS iMovie** to have more control of each photo, movie clips, music and audio in general.

1. In Photos, create and album called **iMovie Project**
1. Add all desired media to this album. Usually you‘ll want to add only media that you marked with ♥︎
1. Go to **iMovie**
1. Create new project with **Movie** profile and add all media from that Photos album
1. Spend some time to learn how to clip and edit animation in iMovie, this is an extremely valuable time to spend
1. Try iMovie‘s new profiles too, as **Storyboard**, for more dramatic and professional look, and **Magic Movie** for machine-learning-curated movies similar to Photos Memories feature
