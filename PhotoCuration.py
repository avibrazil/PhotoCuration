__version__ = '0.5'


# import sys
# sys.path.insert(0,"../..") # Adds higher directory to python modules path.

#### TODO
# - Handle no model tag and fill with other attributes




from iOSbackup import iOSbackup
import sqlite3
import configparser
import sys
import os
import io
# import biplist
import pandas as pd
import numpy as np
import logging
import pprint
import uuid
import tempfile
import copy
import pathlib
from pathlib import Path
import jinja2
# import ffmpeg # pip install ffmpeg-python
import dateutil
import datetime
import pytz
import math
import tempfile
# import exifread
# import mutagen
import re
import json
import subprocess
import NSKeyedUnArchiver







# try:
#     # A powerfull module that can write XMP tags, but available only on Linux
#     import pyexiv2
#
#     # To install this module in Fedora:
#     # (first, as root) dnf install gcc-c++ boost-python3 exiv2-devel python3-devel
#     # (then, as regular user) pip3 install -U py3exiv2 --user
# except (ImportError, RuntimeError):
#     # Module not installed on system (ImportError) or installed but useless on macOS (RuntimeError)
#     pass



# logging.basicConfig(level=logging.DEBUG)
module_logger = logging.getLogger(__name__)



# filenaneTemplate="""{#- -#}
# {% if albums_list != None and albums_list|count > 0 %}{{ creation_local_object.strftime('%Y-%m') }} {{ albums_list[0]|secure }}/{% endif -%}
# {{ creation_local_time_fs }} {% if kind_encoded.startswith('1>') -%}
# ▶️{% elif favorited -%}
# ★{% else -%}
# •{% endif -%}
# {% if suggested_caption is not none %} {{ suggested_caption|secure }}{% endif -%}
# {% if author or camera_model or app_creator %} 【{#- -#}
# {% if author %}{{ author|secure -}}{% endif -%}
# {% if author and (camera_model or app_creator) %}·︎{% endif -%}
# {% if camera_model or app_creator %}{{ (camera_model or app_creator)|secure }}{% endif -%}
# {% if unedited %} original{% endif %}{% if variation %} {{variation}}{% endif %}】{% endif -%}
# {% if collision_index>0 %}~〔{{ "{:02d}".format(collision_index) }}〕{% endif -%}
# .{{ ext -}}
# """



# Filesystem folders from smallest photo album
templateWithFolder="""{#- -#}
{% if album_title != None %}{{ album_period|secure }} {{ album_title|secure }}/{% endif -%}
{{ creation_local_time_fs }} {% if kind_encoded.startswith('1>') -%}
▶️{% elif favorited -%}
★{% else -%}
•{% endif -%}
{% if suggested_caption is not none %} {{ suggested_caption|secure }}{% endif -%}
{% if author or camera_model or app_creator %} 【{#- -#}
{% if author %}{{ author|secure -}}{% endif -%}
{% if author and (camera_model or app_creator) %}·︎{% endif -%}
{% if camera_model or app_creator %}{{ (camera_model or app_creator)|secure }}{% endif -%}
{% if unedited %} original{% endif %}{% if variation %} {{variation}}{% endif %}】{% endif -%}
{% if collision_index>0 %}~〔{{ "{:02d}".format(collision_index) }}〕{% endif -%}
.{{ ext -}}
"""

# No folder for photo album
templateNoFolder="""{#- -#}
{{ creation_local_time_fs }} {% if kind_encoded.startswith('1>') -%}
▶️{% elif favorited -%}
★{% else -%}
•{% endif -%}
{% if suggested_caption is not none %} {{ suggested_caption|secure }}{% endif -%}
{% if author or camera_model or app_creator %} 【{#- -#}
{% if author %}{{ author|secure -}}{% endif -%}
{% if author and (camera_model or app_creator) %}·︎{% endif -%}
{% if camera_model or app_creator %}{{ (camera_model or app_creator)|secure }}{% endif -%}
{% if unedited %} original{% endif %}{% if variation %} {{variation}}{% endif %}】{% endif -%}
{% if collision_index>0 %}~〔{{ "{:02d}".format(collision_index) }}〕{% endif -%}
.{{ ext -}}
"""



class PhotoCuration(object):

    platformFoldersHint={
        'darwin': {
            'config': '~/Library/Application Support/PhotoCuration/photocuration.conf',
        },
        'win32': {
            'config': r'%HOME%\Application Data\Avi Alkalay\PhotoCuration/photocuration.conf',
        },
        'linux': {
            'config': '$HOME/.config/PhotoCuration/photocuration.conf',
        }
    }


    iOSfiles={
        'photos': 'Media/PhotoData/Photos.sqlite',
    }

    photoData="""
            select
                ZASSET.Z_PK as Asset_PK,
                ZASSET.ZDIRECTORY,
                ZASSET.ZFILENAME,
                ZASSET.ZTRASHEDSTATE,
                ZASSET.ZFAVORITE,
                ZASSET.ZWIDTH,
                ZASSET.ZHEIGHT,
                ZMOMENT.ZTITLE as Moment_Title,
                ZMOMENT.ZSUBTITLE as Moment_Subtitle,
                datetime(ZASSET.ZDATECREATED+strftime('%s','2001-01-01'),'unixepoch') as taken,
                ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET,
             -- ZADDITIONALASSETATTRIBUTES.ZEXIFTIMESTAMPSTRING,
                facecount.facecount,
                named_facecount.named_facecount,
                people.Detected_PK,
                people.Person_PK,
                people.short_name,
                people.full_name,
                people.adjustment_ver,
                people.width,
                people.height,
                people.LEFTEYE_pixx,
                people.LEFTEYE_pixy,
                people.RIGHTEYE_pixx,
                people.RIGHTEYE_pixy,
                people.MOUTH_pixx,
                people.MOUTH_pixy,
                people.CENTER_pixx,
                people.CENTER_pixy,
                people.face_size,
                people.person_uri,
                people.person_uuid
            from
                ZASSET

                left outer join ZADDITIONALASSETATTRIBUTES
                    on ZADDITIONALASSETATTRIBUTES.ZASSET=ZASSET.Z_PK

                left outer join ZMOMENT
                    on ZMOMENT.Z_PK= ZASSET.ZMOMENT

                left outer join (
                    select
                        ZDETECTEDFACE.Z_PK as Detected_PK,
                        ZPERSON.Z_PK as Person_PK,
                        ZPERSON.ZDISPLAYNAME as short_name,
                        ZPERSON.ZFULLNAME as full_name,
                        ZDETECTEDFACE.ZADJUSTMENTVERSION as adjustment_ver,
                        ZDETECTEDFACE.ZSOURCEWIDTH as width,
                        ZDETECTEDFACE.ZSOURCEHEIGHT as height,
                        cast(round(ZDETECTEDFACE.ZLEFTEYEX * ZDETECTEDFACE.ZSOURCEWIDTH,0) as integer) LEFTEYE_pixx,
                        cast(round(ZDETECTEDFACE.ZLEFTEYEY * ZDETECTEDFACE.ZSOURCEHEIGHT,0) as integer) LEFTEYE_pixy,
                        cast(round(ZDETECTEDFACE.ZRIGHTEYEX * ZDETECTEDFACE.ZSOURCEWIDTH,0) as integer) RIGHTEYE_pixx,
                        cast(round(ZDETECTEDFACE.ZRIGHTEYEY * ZDETECTEDFACE.ZSOURCEHEIGHT,0) as integer) RIGHTEYE_pixy,
                        cast(round(ZDETECTEDFACE.ZMOUTHX * ZDETECTEDFACE.ZSOURCEWIDTH,0) as integer) MOUTH_pixx,
                        cast(round(ZDETECTEDFACE.ZMOUTHY * ZDETECTEDFACE.ZSOURCEHEIGHT,0) as integer) MOUTH_pixy,
                        cast(round(ZDETECTEDFACE.ZCENTERX * ZDETECTEDFACE.ZSOURCEWIDTH,0) as integer) CENTER_pixx,
                        cast(round(ZDETECTEDFACE.ZCENTERY * ZDETECTEDFACE.ZSOURCEHEIGHT,0) as integer) CENTER_pixy,
                        ZDETECTEDFACE.ZSIZE as face_size, -- face_size×√(width²+height²) = diameter of circle surrounding face
                        ZPERSON.ZPERSONURI as person_uri,
                        ZPERSON.ZPERSONUUID as person_uuid,
                        ZDETECTEDFACE.ZASSET as asset
                    from
                        ZDETECTEDFACE, ZPERSON
                    where
                        ZDETECTEDFACE.ZPERSON=ZPERSON.Z_PK and
                        ZPERSON.ZDISPLAYNAME!=''
                ) as people
                    on people.asset=ZASSET.Z_PK


                left outer join (
                    select
                        ZASSET as asset,
                        count(ZCENTERX) as facecount
                    from ZDETECTEDFACE
                    group by ZASSET
                ) as facecount
                    on facecount.asset=ZASSET.Z_PK


                left outer join (
                    select
                        ZASSET as asset,
                        count(ZCENTERX) as named_facecount
                    from ZDETECTEDFACE, ZPERSON
                    where
                        ZDETECTEDFACE.ZPERSON=ZPERSON.Z_PK and
                        ZPERSON.ZDISPLAYNAME!=''
                    group by ZASSET
                ) as named_facecount
                    on named_facecount.asset=ZASSET.Z_PK


            where
                ZASSET.ZDIRECTORY like 'DCIM%'

            order by
                taken, Detected_PK
    """

    listOfAlbums="""
            select
                ZGENERICALBUM.Z_PK as album_pk,
                ZGENERICALBUM.ZUUID as album_uuid,
                ZGENERICALBUM.ZTITLE as album_title,
                ZGENERICALBUM.ZPUBLICURL as album_public_url,
                ZGENERICALBUM.ZCACHEDCOUNT as album_asset_count,
                ZGENERICALBUM.ZCACHEDPHOTOSCOUNT as album_photo_count,
                ZGENERICALBUM.ZCACHEDVIDEOSCOUNT as album_video_count,
                ZGENERICALBUM.ZCLOUDDELETESTATE as album_cloud_deleted_state,
                ZGENERICALBUM.ZCLOUDLOCALSTATE as album_cloud_local_state,
                ZGENERICALBUM.ZCUSTOMSORTASCENDING as album_custom_sort_ascending,
                ZGENERICALBUM.ZCUSTOMSORTKEY as album_custom_sort_key,
            --  ZGENERICALBUM.ZISPINNED,
            --  ZGENERICALBUM.ZISPROTOTYPE,
                ZGENERICALBUM.ZKIND, -- 1505 is iCloud album
                ZGENERICALBUM.ZPENDINGITEMSCOUNT,
                ZGENERICALBUM.ZPENDINGITEMSTYPE,
                ZGENERICALBUM.ZSYNCEVENTORDERKEY,
                ZGENERICALBUM.ZTRASHEDSTATE as album_is_trashed,
                ZGENERICALBUM.ZCUSTOMKEYASSET,
                ZGENERICALBUM.ZKEYASSET,
                ZGENERICALBUM.ZSECONDARYKEYASSET,
                ZGENERICALBUM.ZTERTIARYKEYASSET,
                ZGENERICALBUM.ZCLOUDALBUMSUBTYPE,
                ZGENERICALBUM.ZCLOUDMULTIPLECONTRIBUTORSENABLED,
                ZGENERICALBUM.ZCLOUDMULTIPLECONTRIBUTORSENABLEDLOCAL,
                ZGENERICALBUM.ZCLOUDNOTIFICATIONSENABLED,
                ZGENERICALBUM.ZCLOUDOWNEREMAILKEY,
                ZGENERICALBUM.ZCLOUDOWNERISWHITELISTED,
                ZGENERICALBUM.ZCLOUDPUBLICURLENABLED,
                ZGENERICALBUM.ZCLOUDPUBLICURLENABLEDLOCAL,
                ZGENERICALBUM.ZCLOUDRELATIONSHIPSTATE,
                ZGENERICALBUM.ZCLOUDRELATIONSHIPSTATELOCAL,
                ZGENERICALBUM.ZHASUNSEENCONTENT,
                ZGENERICALBUM.ZISOWNED,
                ZGENERICALBUM.ZUNSEENASSETSCOUNT,
                ZGENERICALBUM.ZKEYASSETFACEIDENTIFIER,
                ZGENERICALBUM.ZKEYASSETFACETHUMBNAILINDEX,

                ZGENERICALBUM.ZPARENTFOLDER as album_parent_folder,
                ZGENERICALBUM.Z_FOK_PARENTFOLDER as album_parent_folder_pk,

                datetime(ZGENERICALBUM.ZCREATIONDATE+strftime('%s', '2001-01-01'), 'unixepoch') as album_utc_creation,
                datetime(ZGENERICALBUM.ZSTARTDATE+strftime('%s', '2001-01-01'), 'unixepoch') as album_utc_start,
                datetime(ZGENERICALBUM.ZENDDATE+strftime('%s', '2001-01-01'), 'unixepoch') as album_utc_end,

                ZGENERICALBUM.ZTRASHEDDATE,
                ZGENERICALBUM.ZCLOUDCREATIONDATE,
                ZGENERICALBUM.ZCLOUDLASTCONTRIBUTIONDATE,
                ZGENERICALBUM.ZCLOUDLASTINTERESTINGCHANGEDATE,
                ZGENERICALBUM.ZCLOUDSUBSCRIPTIONDATE,
                ZGENERICALBUM.ZCLOUDGUID,
                ZGENERICALBUM.ZIMPORTSESSIONID,
                ZGENERICALBUM.ZCLOUDOWNERFIRSTNAME,
                ZGENERICALBUM.ZCLOUDOWNERFULLNAME,
                ZGENERICALBUM.ZCLOUDOWNERHASHEDPERSONID,
                ZGENERICALBUM.ZCLOUDOWNERLASTNAME,
                ZGENERICALBUM.ZCLOUDPERSONID,
                ZGENERICALBUM.ZPROJECTDOCUMENTTYPE,
                ZGENERICALBUM.ZPROJECTEXTENSIONIDENTIFIER,
                ZGENERICALBUM.ZPROJECTRENDERUUID,
                ZGENERICALBUM.ZCUSTOMQUERYTYPE
            from ZGENERICALBUM
            where
                ZTRASHEDSTATE = 0 AND
                ZTITLE not NULL AND
                ZKIND not between 3500 and 3600
    """
#     Albums:
#         ZKIND:
#             1505: iCloud
#             2: Regular
#             1506: ???? (ZTITLE always NULL)
#             16??: ???? (ZTITLE always NULL)
#             35??: iOS internal operations (ZTITLE in (progress-sync, progress-ota-restore, progress-fs-import))
#             3900 and up: ????
    
    

    assetTypes={ # match with `kind_encoded` from `listOfAssets` query
        '0>0':     'image', # JPG, HEIC, PNG, GIF
        '0>0>2':   'animated GIF',
        '0>1':     'panorama',
        '0>10':    'screenshot',
        '0>0>1>2': 'part of burst',
        '0>2>3>0': 'live photo',
        '0>2>5>1': 'live photo, loop effect',
        '0>2>5>2': 'live photo, bounce effect',
        '0>2>3>3': 'long exposure from live photo',
        '1>0':     'video',
        '1>101':   'slow motion video',
        '1>102':   'timelapse video',
        '1>103':   'screencast'
    }



    listOfAssets="""
            select
                ZASSET.Z_PK as Asset_PK,
                ZASSET.ZDIRECTORY as dcim_folder,
                ZASSET.ZFILENAME as original_file,
                ZASSETDESCRIPTION.ZLONGDESCRIPTION as caption,
                ZASSET.ZTRASHEDSTATE as trashed,
                ZASSET.ZHASADJUSTMENTS as edited,
                case
                    when ZASSET.ZKIND=0 then case -- images
                        when ZASSET.ZKINDSUBTYPE=2 then '0>'||ZASSET.ZKINDSUBTYPE||'>'||ZASSET.ZPLAYBACKSTYLE||'>'||ZASSET.ZPLAYBACKVARIATION
                        when ZASSET.ZPLAYBACKSTYLE=2 then '0>'||ZASSET.ZKINDSUBTYPE||'>'||ZASSET.ZPLAYBACKSTYLE
                        when ZASSET.ZVISIBILITYSTATE=2 then '0>'||ZASSET.ZKINDSUBTYPE||'>'||ZASSET.ZPLAYBACKSTYLE||'>'||ZASSET.ZVISIBILITYSTATE
                        else '0>'||ZASSET.ZKINDSUBTYPE
                    end
                    when ZASSET.ZKIND=1 then ZASSET.ZKIND||'>'||ZASSET.ZKINDSUBTYPE --videos
                end as kind_encoded,
                case
                    when ZASSET.ZKIND=0 then case -- images
                        when ZASSET.ZKINDSUBTYPE=0 then case
                            when ZASSET.ZPLAYBACKSTYLE=2 then 'animated GIF'
                            when ZASSET.ZVISIBILITYSTATE=2 then 'part of burst'
                            else 'image' -- check ZCREATORBUNDLEID if its a PNG
                        end
                        when ZASSET.ZKINDSUBTYPE=1 then 'panorama'
                        when ZASSET.ZKINDSUBTYPE=10 then 'screenshot' -- created by this device
                        when ZASSET.ZKINDSUBTYPE=2 then case -- live photos
                            when ZASSET.ZPLAYBACKSTYLE=3 then case
                                when ZASSET.ZPLAYBACKVARIATION=0 then 'live photo'
                                when ZASSET.ZPLAYBACKVARIATION=3 then 'long exposure from live photo'
                            end
                            when ZASSET.ZPLAYBACKSTYLE=5 then case
                                when ZASSET.ZPLAYBACKVARIATION=1 then 'live photo, loop effect'
                                when ZASSET.ZPLAYBACKVARIATION=2 then 'live photo, bounce effect'
                            end
                        end
                    end
                    when ZASSET.ZKIND=1 then case -- videos
                        when ZASSET.ZKINDSUBTYPE=0 then 'video'
                        when ZASSET.ZKINDSUBTYPE=101 then 'slow motion video'
                        when ZASSET.ZKINDSUBTYPE=102 then 'timelapse video'
                        when ZASSET.ZKINDSUBTYPE=103 then 'screencast'
                    end
                end as kind_description,
                case
                    when ZASSET.ZFAVORITE=0 then NULL
                    else ZASSET.ZFAVORITE
                end as favorited,
                ZASSET.ZWIDTH as width,
                ZASSET.ZHEIGHT as height,
                ZASSET.ZDURATION as video_duration,
                ZASSET.ZUUID as uuid,
                ZMOMENT.ZTITLE as moment_title,
                ZMOMENT.ZSUBTITLE as moment_subtitle,
                ZASSET.ZDATECREATED as creation_timestamp,
                datetime(ZASSET.ZDATECREATED+strftime('%s','2001-01-01'),'unixepoch') as utc_time,
                coalesce(ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET,ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET) as tz_offset,
                datetime(ZASSET.ZDATECREATED+coalesce(ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET,ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET)+strftime('%s','2001-01-01'),'unixepoch') as asset_local_time,
                ZADDITIONALASSETATTRIBUTES.ZEXIFTIMESTAMPSTRING as exif_timestamp,
                ZASSET.ZLATITUDE as latitude,
                ZASSET.ZLONGITUDE  as longitude,
                ZADDITIONALASSETATTRIBUTES.ZREVERSELOCATIONDATA as location_data,
                ZADDITIONALASSETATTRIBUTES.ZIMPORTEDBYBUNDLEIDENTIFIER as app_creator,
                ZADDITIONALASSETATTRIBUTES.ZEDITORBUNDLEID as app_editor,
                coalesce(ZADDITIONALASSETATTRIBUTES.ZIMPORTEDBYBUNDLEIDENTIFIER,ZADDITIONALASSETATTRIBUTES.ZEDITORBUNDLEID) as app_creator_or_editor,
                ZEXTENDEDATTRIBUTES.ZCAMERAMAKE as camera_make,
                ZEXTENDEDATTRIBUTES.ZCAMERAMODEL as camera_model,
                ZEXTENDEDATTRIBUTES.ZLENSMODEL as lens_model,
                facecount.facecount,
                named_facecount.named_facecount
            from
                ZASSET

                left outer join ZADDITIONALASSETATTRIBUTES
                    on ZADDITIONALASSETATTRIBUTES.ZASSET=ZASSET.Z_PK

                left outer join ZEXTENDEDATTRIBUTES
                    on ZEXTENDEDATTRIBUTES.ZASSET=ZASSET.Z_PK

                left outer join ZASSETDESCRIPTION
                    on ZASSETDESCRIPTION.ZASSETATTRIBUTES=ZADDITIONALASSETATTRIBUTES.Z_PK

                left outer join ZMOMENT
                    on ZMOMENT.Z_PK=ZASSET.ZMOMENT

                left outer join (
                    select
                        ZASSET as asset,
                        count(ZCENTERX) as facecount
                    from ZDETECTEDFACE
                    group by ZASSET
                ) as facecount
                    on facecount.asset=ZASSET.Z_PK

                left outer join (
                    select
                        ZASSET as asset,
                        count(ZCENTERX) as named_facecount
                    from ZDETECTEDFACE, ZPERSON
                    where
                        ZDETECTEDFACE.ZPERSON=ZPERSON.Z_PK and
                        ZPERSON.ZDISPLAYNAME!=''
                    group by ZASSET
                ) as named_facecount
                    on named_facecount.asset=ZASSET.Z_PK

            where
                ZASSET.ZDIRECTORY like 'DCIM%'
            order by Asset_PK
    """

    listOfMemories="""
            select
                ZMEMORY.Z_PK as memory_pk,
                ZMEMORY.ZCATEGORY as memory_category,
                ZMEMORY.ZFAVORITE as memory_favorited,
                ZMEMORY.ZFEATUREDSTATE as memory_featured,
                ZMEMORY.ZSUBCATEGORY as memory_subcategory,
                -- ZMEMORY.ZUSERCREATED as memory_usercreated,
                ZMEMORY.ZVIEWCOUNT as memory_viewcount,
                ZMEMORY.ZKEYASSET as memory_keyasset,
                datetime(ZMEMORY.ZCREATIONDATE+strftime('%s', '2001-01-01'), 'unixepoch') as memory_utc_creation,
                ZMEMORY.ZSCORE as memory_score,
                replace(ZMEMORY.ZTITLE, '\n','') as memory_title,
                ZMEMORY.ZSUBTITLE as memory_subtitle,
                ZMEMORY.ZUUID as memory_uuid,
                ZMEMORY.ZMOVIEASSETSTATE,
                ZMEMORY.ZMOVIEDATA,
                ZMEMORY.ZPHOTOSGRAPHDATA,
                ZMEMORY.ZREJECTED as trashed
            from ZMEMORY
            where ZMEMORY.ZREJECTED!=1

    """

    assetsForMoments="""
            select
                ZMOMENT.Z_PK as moment_pk,
                ZASSET.ZMOMENT as asset_moment,

                ZMOMENT.ZTITLE as moment_title,
                ZMOMENT.ZSUBTITLE as moment_subtitle,

                ZMOMENT.ZCACHEDCOUNT as moment_asset_count,
                ZMOMENT.ZCACHEDPHOTOSCOUNT as moment_photo_count,
                ZMOMENT.ZCACHEDVIDEOSCOUNT as moment_video_count,
                ZMOMENT.ZTRASHEDSTATE as moment_is_trashed,
                datetime(ZMOMENT.ZSTARTDATE+strftime('%s', '2001-01-01'), 'unixepoch') as moment_utc_start,
                datetime(ZMOMENT.ZENDDATE+strftime('%s', '2001-01-01'), 'unixepoch') as moment_utc_end,
                datetime(ZMOMENT.ZSTARTDATE+ZMOMENT.ZTIMEZONEOFFSET+strftime('%s', '2001-01-01'), 'unixepoch') as moment_momenttime_start,
                datetime(ZMOMENT.ZENDDATE+ZMOMENT.ZTIMEZONEOFFSET+strftime('%s', '2001-01-01'), 'unixepoch') as moment_momenttime_end,

                datetime(ZASSET.ZDATECREATED+strftime('%s', '2001-01-01'), 'unixepoch') as asset_utc_created,
                ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET as asset_infered_timezone,
                datetime(ZASSET.ZDATECREATED+ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET+strftime('%s', '2001-01-01'), 'unixepoch') as asset_assettime_created,

                ZASSET.Z_PK as asset_pk,
                ZASSET.ZDIRECTORY as asset_diretcory,
                ZASSET.ZFILENAME as asset_filename
            from ZMOMENT
            left outer join ZASSET
                on ZASSET.ZDATECREATED between ZMOMENT.ZSTARTDATE and ZMOMENT.ZENDDATE
            left outer join ZADDITIONALASSETATTRIBUTES
                on ZADDITIONALASSETATTRIBUTES.Z_PK=ZASSET.Z_PK
            where moment_title is not NULL;
    """

    facesForAssets="""
        WITH

            face AS (
                SELECT zasset AS asset
                    ,zperson AS person
                    ,cast(round(zsize * sqrt(zsourcewidth * zsourcewidth + zsourceheight * zsourceheight)) AS INTEGER) AS size
                    ,cast(round(zcenterx * zsourcewidth) AS INTEGER) AS centerx
                    ,cast(round(zcentery * zsourceheight) AS INTEGER) AS centery
                FROM zdetectedface
                WHERE zasset NOT NULL
            ),

            person AS (
                SELECT z_pk AS id
                    ,zdisplayname AS short_name
                    ,zfullname AS full_name
                    ,zpersonuri AS uri
                    ,zpersonuuid AS uuid
                FROM zperson
                WHERE zdisplayname <> ''
            )

        SELECT
            face.asset
            ,face.size
            ,face.centerx
            ,face.centery
            ,face.person AS person_id
            ,person.uri AS person_uri
            ,person.uuid AS person_uuid
            ,person.short_name
            ,person.full_name
        FROM face,person
        WHERE person.id = face.person
        ORDER BY
            face.asset,
            face.size DESC
    """

    domain='CameraRollDomain'

    original='Media/{dcim_folder}/{file}'
    mutation='Media/PhotoData/Mutations/{dcim_folder}/{file_no_extension}/Adjustments/FullSizeRender.{file_extension}'

    referenceFPS=30 # Convert slowmotion (240fps) to this reference FPS

    def __init__(self,
                configFile=None,
                backupRoot=None,
                udid=None,
                backupPassword=None,
                backupDerivedKey=None
        ):

        self.logger=logging.getLogger('{a}.{b}'.format(a=__name__, b=type(self).__name__))

        self.j2=jinja2.Environment()
        self.j2.filters['secure']=PhotoCuration.secureFileName

        self.iosDBs={}
        self.loadConfig(configFile)
        self.logger.debug(dict(self.config))

#         backuproot=None
#         if 'global' in self.config and 'backup' in self.config['global']:
#             backuproot=self.config['global']['backup']

        self.ios=iOSbackup(udid=udid, derivedkey=backupDerivedKey, backuproot=backupRoot)
        self.getiOSfiles()
        self.getPhotoDB()
        self.curated=False
        self.tagger=Tagger()


    def curate(self,
                author=None, # author of photos
                deviceOwner=None,
    ):
        self.author=author
        self.device_owner=deviceOwner

        if self.curated == False:
            self.fetchAssets()
            self.fetchAuthor()
            self.fetchAlbums()
            self.fetchMemories()
            self.fetchPeople()
            self.calcAssetsKeywords()
            self.fetchPlacesMoments()
            self.addAssetNameFromSmallestAlbum()
            self.addAssetNameFromSmallestMemory()
            self.calcBestLocationName()
            self.calcBestAssetCaption()

            self.curated=True

        # self.extractAndTag()




    def __del__(self):
        self.close()



    def close(self):
        self.db.close()
        self.ios.close()
        for f in self.iosDBs:
            try:
                os.remove(self.iosDBs[f]['decryptedFilePath'])
            except FileNotFoundError:
                # Its OK if Photos database temporary file is not there anymore
                pass


    def secureFileName(string):
        if string:
            replace1={
                '...': '…',
                '#': '♯',
                ':': '∶',
                '?': '⁇',
                '/': '／',
                '\\': '＼',
                '\|': '￨',
                '>': '＞',
                '<': '＜',
                '*': '✱',
                '&': '＆'
            }

            replace2={
                r'"(.*?)"': r'“\1”',
                r"'(.*?)'": r'‘\1’'
            }

            pattern = re.compile("|".join([re.escape(x) for x in sorted(replace1,key=len,reverse=True)]), flags=re.DOTALL)
            simple=pattern.sub(lambda x: replace1[x.group(0)], string)
            comple=simple
            for r in replace2:
                comple=re.sub(r,replace2[r],comple)
            return comple



    def fetchAuthor(self):
        camera_model_to_author_map=None
        if isinstance(self.author, list):
            camera_model_to_author_map=(
                pd.DataFrame(
                    self.author,
                    columns=('camera_model','start','end','author')
                )
                .assign(
                    start=lambda table: table.start.fillna(pd.Timestamp.min),
                    end=lambda table: table.end.fillna(pd.Timestamp.max),
                )
            )
            self.author=None

        if self.author is None:
            self.author=self.device_owner

        # Set a default author for all assets
        self.assets['author']=self.author

        # Set author based on device type and time range
        if camera_model_to_author_map is not None:
            for i,spec in camera_model_to_author_map.iterrows():
                self.assets.loc[(self.assets.camera_model==spec.camera_model) & (self.assets.asset_local_time.between(spec.start,spec.end)), 'author']=spec.author



    def extractAndTag(self,
                start=None,
                end=None,
                extractTypes=None,
                target=None, # folder to receive files
                originals=['1>101', '0>2>3>0', '0>2>3>3', '0>2>5>1', '0>2>5>2'], # either to extract also originals or not
                trashed=False,
                filenameTemplate=templateWithFolder
    ):
        if start:
            self.start=pd.Timestamp(start).to_pydatetime()
        else:
            self.start=start

        if end:
           self.end=pd.Timestamp(end).to_pydatetime()
        else:
            self.end=end

        self.target=target
        self.trashed=trashed
        self.extractTypes=extractTypes

        # Handling of originals
        self.originals=originals

        self.filenameTemplate=self.j2.from_string(filenameTemplate)

        if self.target:
            Path(self.target).mkdir(parents=True, exist_ok=True)

        # At this point, this is the columns we have on self.assets:
        # Index(['dcim_folder', 'file', 'caption', 'trashed', 'kind', 'favorited',
        #        'width', 'height', 'video_duration', 'uuid', 'moment_title',
        #        'moment_subtitle', 'creation_timestamp', 'utc_time', 'tz_offset',
        #        'asset_local_time', 'exif_timestamp', 'facecount', 'named_facecount',
        #        'location_name', 'location_context', 'location_street', 'album_period'
        #        'location_subLocality', 'location_city', 'location_adminArea',
        #        'location_state', 'location_country', 'location_postalCode',
        #        'location_countryCode', 'location_formattedAddress', 'album_title',
        #        'memory_title', 'memory_subtitle', 'location_suggested_name',
        #        'infered_asset_caption', 'infered_asset_caption_score'],
        #       dtype='object')

        filter=[]

        if self.trashed == False:
            filter.append('trashed in [0]')

        if self.start:
            filter.append('asset_local_time >= @self.start')

        if self.end:
            filter.append('asset_local_time <= @self.end')


        if self.extractTypes:
            filter.append('kind_encoded in @self.extractTypes')


        filters=') and ('.join(filter)
        filters=f'({filters})'

#         print(filters)

        self.tags=self.assets.query(filters).sort_values(by='utc_time')[[
            'dcim_folder',
            'original_file',
            'edited',
            'infered_asset_caption',
            'kind_encoded',
            'kind_description',
            'favorited',
            'width',
            'height',
            'video_duration',
            'uuid',
            'latitude',
            'longitude',
            'location_suggested_name',
            'location_name',
            'location_context',
            'location_street',
            'location_subLocality',
            'location_city',
            'location_adminArea',
            'location_state',
            'location_country',
            'location_postalCode',
            'location_countryCode',
            'location_formattedAddress',
            'utc_time',
            'asset_local_time',
            'tz_offset',
            'infered_asset_caption_score',
            'author',
            'device_owner',
            'device_hostname',
            'device_ios_version',
            'device_ios_build',
            'device_serial_number',
            'device_product_type',
            'app_creator',
            'app_editor',
            'app_creator_or_editor',
            'keywords',
            'album_title',
            'album_period',
            'albums_list',
            'memories_list',
            'people_list'
        ]].copy()


        self.tags['favorited_percent']=100*self.tags['favorited']
        self.tags['favorited_5stars']=5*self.tags['favorited']

        renames={
            'infered_asset_caption': 'suggested_caption',
            'infered_asset_caption_score': 'suggested_caption_score',
            'asset_local_time': 'creation_local_object',
            'utc_time': 'creation_utc_object'
        }
        self.tags.rename(renames, axis='columns', inplace=True)

        # self.tags['author']=self.author

        # Merge naive local time with tz_offset into a TZ-aware datetime
        self.tags['creation_local_object']=self.tags.apply(
            # Pandas Series only support Timestamps with same timezones.
            # If multiple timezones, an object Series will be created, not datetime.
            lambda w: w['creation_local_object'].tz_localize(pytz.FixedOffset(w['tz_offset']/60)),
            axis=1
        )

        PhotoCuration.itemizeDatetime(self.tags, 'creation_local_object', 'creation_local')
        PhotoCuration.itemizeDatetime(self.tags, 'creation_utc_object', 'creation_utc')

        # Convert Pandas' NA into Python-native None, for increased compatibility with Jinja
        self.tags=self.tags.astype(object)
        for c in self.tags.columns:
            self.tags[c].loc[pd.isna(self.tags[c])]=None
#         self.tags.replace([np.nan], [None], inplace=True)

        # Database tags are ready to be used. Now get tags from file.

        if self.originals:
            originalHandling=[False,True]
        else:
            originalHandling=[False]

        for assetCurrent in self.tags.iterrows():
            assetCurrent={
                'pk': assetCurrent[0],
                'incarnations': {
                    'master': {
                        # All assets will have a 'master' spawn which is
                        # the user edited version of photo/video, but it
                        # might be the original too if unedited.
                        # Other spawn might be slowmotion, original etc.
                        'tags': dict(assetCurrent[1]),
                    }
                }
            }

            # Merge timezone offset into creation_local_object
#             assetCurrent['incarnations']['master']['tags']['creation_local_object']=(
#                 assetCurrent['incarnations']['master']['tags']['creation_local_object']
#                 .tz_localize(
#                     pytz.FixedOffset(
#                         assetCurrent['incarnations']['master']['tags']['tz_offset']/60
#                     )
#                 )
#             )

            # Get people and faces of asset
            assetCurrent['incarnations']['master']['people']=self.getAssetPeople(assetCurrent['pk'])

            # initialize file name collision handling artifacts
            assetCurrent['incarnations']['master']['tags']['collision_index'] = 0
            assetCurrent['incarnations']['master']['tags']['original_file_no_extension']=os.path.splitext(assetCurrent['incarnations']['master']['tags']['original_file'])[0]
            assetCurrent['incarnations']['master']['tags']['original_file_extension']=os.path.splitext(assetCurrent['incarnations']['master']['tags']['original_file'])[1][1:].strip().lower()


            self.logger.info("Working on {} [{}] “{}”".format(
                assetCurrent['incarnations']['master']['tags']['original_file'],
                assetCurrent['incarnations']['master']['tags']['creation_local_object'].isoformat(),
                assetCurrent['incarnations']['master']['tags']['suggested_caption']
            ))


            try:
                del self.assetCurrent
            except AttributeError:
                pass

            self.assetCurrent=assetCurrent

            # self.logger.debug('MultiHandling')

            if (
                assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>0') or
                assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>1') or
                assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>10')
                # and 'gif' not in assetCurrent['incarnations']['master']['tags']['original_file_extension']
            ):
                # Regular image as JPG, HEIC, PNG, GIF, DNG
                self.handleImage(assetCurrent)

#             if assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>10'):
#                 # Regular image as JPG, HEIC, PNG, GIF, DNG
#                 self.handleImage(assetCurrent)

            if assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('1>'):
                # Various types of video
                self.logger.debug('Handling video')
                self.handleVideo(assetCurrent)

            if assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>2'):
                # Its a Live photo...


                # Handle Live photos, the image part
                self.handleImage(assetCurrent)

#                 if assetCurrent['incarnations']['master']['tags']['kind_encoded'] != '0>2>3>3':



                # Now morph it into a video to handle the video part
                self.logger.debug(f"Handling video part of Live Photo {assetCurrent['incarnations']['master']['tags']['original_file']}")

                # Delete image incarnations to start fresh
                deletes=set(assetCurrent['incarnations'].keys())
                deletes.remove('master')
                for i in deletes:
                    # Delete all incarnations except 'master'
                    del assetCurrent['incarnations'][i]

                assetCurrent['incarnations']['master']['tags']['original_file']=assetCurrent['incarnations']['master']['tags']['original_file_no_extension']+'.MOV'
                assetCurrent['incarnations']['master']['tags']['original_file_extension']='mov'
                self.handleVideo(assetCurrent)

        # if self.tagger:
        #     del self.tagger




    def getAssetPeople(self,assetPK):

        faceKeyMap={
            'Name': 'full_name',
            'ShortName': 'short_name',
            'person_uri': 'person_uri',
            'person_uuid': 'person_uuid',
            'person_id': 'Person_PK',

            'Area/center_xpix': 'CENTER_pixx',
            'Area/center_ypix': 'CENTER_pixy',

            'Area/center_xnormal': 'CENTER_normalizedx',
            'Area/center_ynormal': 'CENTER_normalizedy',

            'Area/facesize_normal': 'face_size',

            'Area/righteye_xpix': 'RIGHTEYE_pixx',
            'Area/righteye_ypix': 'RIGHTEYE_pixy',
            'Area/lefteye_xpix': 'LEFTEYE_pixx',
            'Area/lefteye_ypix': 'LEFTEYE_pixy',
            'Area/mouth_xpix': 'MOUTH_pixx',
            'Area/mouth_ypix': 'MOUTH_pixy',
        }

        regions=[
            dict(
                Name=f['full_name'],
                Type='Face',
                Area=dict(
                    x=f['centerx']-f['size']/2,
                    y=f['centery']-f['size']/2,
                    w=f['size'],
                    h=f['size'],
                )
            )
            for i,f in self.peopleOfAssets[self.peopleOfAssets['asset']==assetPK].iterrows()
        ]

        if len(regions)>0:
            return regions
        else:
            return None





    def handleVideo(self, asset):
        import ffmpeg # pip install ffmpeg-python


        # Get original video timecodes

        currentIncarnation=asset['incarnations']['master']


        #mark BEGIN read original video and metadata

        currentIncarnation['backupfile']=self.original.format(
            dcim_folder=currentIncarnation['tags']['dcim_folder'],
            file=currentIncarnation['tags']['original_file']
        )

        # Extract image from iOS backup and put it into target folder with a temporary name
        self.logger.debug(f"Going to extract {currentIncarnation['backupfile']}")

        currentIncarnation['decryptedFileInfo']=self.ios.getFileDecryptedCopy(
            relativePath=currentIncarnation['backupfile'],
            targetFolder=self.target
        )

#         self.logger.debug(f"ffprobe {currentIncarnation['decryptedFileInfo']['decryptedFilePath']}")
#         currentIncarnation['meta']=ffmpeg.probe(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])
#         currentIncarnation['tags']=(
#             currentIncarnation['tags']
#             .append(
#                 pd.Series(self.tagger.getTags(
#                     currentIncarnation['decryptedFileInfo']['decryptedFilePath']
#                 ))
#             )
#         )

        currentIncarnation['tags'].update(
            self.tagger.getTags(
                    currentIncarnation['decryptedFileInfo']['decryptedFilePath']
            )
        )



#         metaToTags=[
#             # ffprobe bindings
#             ('media_create_time', 'creation_time'),
#             ('camera_make', 'com.apple.quicktime.make'), # Apple
#             ('camera_model', 'com.apple.quicktime.model'), # iPhone 11 Pro
#             ('camera_software_version', 'com.apple.quicktime.software') # 14.2
#         ]

        # Get video number of frames per second; useful to handle slow motion videos
#         for i in range(5):
#             try:
#                 # Try to find video on i-nth track
#                 currentIncarnation['tags']['framerate']=currentIncarnation['meta']['streams'][i]['avg_frame_rate']
#                 currentIncarnation['tags']['framerate']=currentIncarnation['tags']['framerate'].split('/')
#                 currentIncarnation['tags']['framerate']=int(currentIncarnation['tags']['framerate'][0])/int(currentIncarnation['tags']['framerate'][1])
#
#                 # If we reached this point, everything was good and we found a valid framerate.
#                 # No need to continue.
#                 break
#             except ZeroDivisionError:
#                 # Simply continue to next track if video not found on this track
#                 pass

        # Update the tags dict with video tags extracted from file
#         for varname,tagname in metaToTags:
#             try:
#                 currentIncarnation['tags'][varname]=currentIncarnation['meta']['format']['tags'][tagname]
#             except KeyError:
#                 # desired tag unavailable in video, so ignore it.
#                 pass

        # Get video file create time; useful to calculate wall clock duration of unclipped time lapse videos
        currentIncarnation['tags']['media_create_time']=(
            dateutil.parser.parse(
                currentIncarnation['tags']['media_create_time'].replace(':','-',2)
            )
        )

        if 'video_codec' in currentIncarnation['tags']:
            currentIncarnation['tags']['video_codec']=currentIncarnation['tags']['video_codec'].replace('.','')
        else:
            # Some Instagram videos doesn't set exiftool’s 'QuickTime:CompressorName'.
            # But we need it to be used as file extension for some conversion operations of slow motion videos.
            # We are going to set it as 'h264' as default even if not used in Instagram situations.
            currentIncarnation['tags']['video_codec']='h264'


        # Get video duration
#         currentIncarnation['tags']['video_duration']=float(currentIncarnation['meta']['format']['duration'])
#         currentIncarnation['tags']['video_duration']=sum(
#             x * float(t) for x, t in zip([1, 60, 3600], reversed(currentIncarnation['tags']['video_duration'].replace(' s','').split(":")))
#         )

        #mark END read original video and metadata


        #mark BEGIN basic decisions about slowmotion, timelapse etc

        if '1>102' in currentIncarnation['tags']['kind_encoded']:
            # Timelapse videos recording time is the time media was created minus the time the recording was started
            currentIncarnation['tags']['variation']='timelapse'
            currentIncarnation['tags']['recording_duration']=(
                pd.Timestamp(currentIncarnation['tags']['media_create_time'],tz='UTC')-
                currentIncarnation['tags']['creation_utc_object']
            ).total_seconds()
        else:
            # Regular videos
            currentIncarnation['tags']['recording_duration']=currentIncarnation['tags']['video_duration']

        #mark END basic decisions about slowmotion, timelapse etc

        #mark BEGIN check for mutation and produce other incarnations
        if asset['incarnations']['master']['tags']['edited']:
            if (type(self.originals) is bool and self.originals) or (type(self.originals) is list and asset['incarnations']['master']['tags']['kind_encoded'] in self.originals):
                # Create an incarnation for the original based on the master and mark it as unedited
                asset['incarnations']['original']=copy.deepcopy(asset['incarnations']['master'])
                asset['incarnations']['original']['tags']['unedited']=True

            # Create the main incarnation
            asset['incarnations']['main']=copy.deepcopy(asset['incarnations']['master'])

            asset['incarnations']['main']['backupfile']=self.mutation.format(
                dcim_folder=asset['incarnations']['main']['tags']['dcim_folder'],
                file_no_extension=asset['incarnations']['main']['tags']['original_file_no_extension'],
                file_extension=asset['incarnations']['main']['tags']['original_file_extension'],
            )
        else:
            # The 'main' incarnation is the original file
            asset['incarnations']['main']=copy.deepcopy(asset['incarnations']['master'])


        if currentIncarnation['tags']['kind_encoded'].startswith('1>101'):
            # Slowmotion also export a true slow motion video with 30fps along with the original high frame rate media
            asset['incarnations']['originalslow']=copy.deepcopy(asset['incarnations']['master'])
            asset['incarnations']['originalslow']['tags']['variation']='slowmotion'
            asset['incarnations']['originalslow']['tags']['newfps']=self.referenceFPS

            # video duration on wannabe slow motion videos is fps/newfps times longer
            # d₁ = d₀ × framerate ÷ newfps

            asset['incarnations']['originalslow']['tags']['video_duration']*=(
                asset['incarnations']['originalslow']['tags']['framerate']/
                asset['incarnations']['originalslow']['tags']['newfps']
            )


        #mark END check for mutation and produce other incarnations



        self.logger.debug("Incarnations: " + str(asset['incarnations']))


        # At this point we have all incarnations that we desire, mostly 'main' and 'original'



        #mark BEGIN iterate over all incarnations
        for incarnation in asset['incarnations']:
            if 'master' in incarnation:
                # 'master' is not a real incarnation we have to handle, so skip it
                continue

            currentIncarnation=asset['incarnations'][incarnation]

            # Extract image from iOS backup and put it into target folder with a temporary name
            try:
                if currentIncarnation['backupfile']!=asset['incarnations']['master']['backupfile']:
                    # Extract asset only if not extracted by master incarnation
                    currentIncarnation['decryptedFileInfo']=self.ios.getFileDecryptedCopy(
                        relativePath=currentIncarnation['backupfile'],
                        targetFolder=self.target
                    )
            except FileNotFoundError:
                # Not a real mutation, happens on slowmotion videos; just skip it
                self.logger.warning(f"File not found: {currentIncarnation['backupfile']}")
                continue

            currentIncarnation['tags']['ext'] = (
                os.path.splitext(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])[1][1:]
                .strip()
                .lower()
            )

#             self.logger.debug(f"ffprobe {currentIncarnation['decryptedFileInfo']['decryptedFilePath']}")
#             currentIncarnation['meta']=ffmpeg.probe(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])
            currentIncarnation['tags'].update(
                self.tagger.getTags(
                        currentIncarnation['decryptedFileInfo']['decryptedFilePath']
                )
            )

            currentIncarnation['tags']['media_create_time']=(
                dateutil.parser.parse(
                    currentIncarnation['tags']['media_create_time'].replace(':','-',2)
                )
            )

            currentIncarnation['tags']['video_codec']=currentIncarnation['tags']['video_codec'].replace('.','')

#             metaToTags=[
#                 # exifread bindings
#                 ('camera_make', 'com.apple.quicktime.make'), # Apple
#                 ('camera_model', 'com.apple.quicktime.model'), # iPhone 11 Pro
#                 ('camera_software_version', 'com.apple.quicktime.software'), # 14.2
#                 ('tag_creation_date','com.apple.quicktime.creationdate'), #=2020-11-07T16:42:21-0300
#                 ('location_accuracy_horizontal', 'com.apple.quicktime.location.accuracy.horizontal'), #=65.000000
#                 ('location_ISO6709', 'com.apple.quicktime.location.ISO6709') #=-23.5506-046.6835+792.764/
#             ]
#
#             # Update the tags dict with video tags extracted from file
#             for varname,tagname in metaToTags:
#                 try:
#                     currentIncarnation['tags'][varname]=currentIncarnation['meta']['format']['tags'][tagname]
#                 except KeyError:
#                     # information for 'tagname' unavailable in video, so ignore it.
#                     pass
#
#             # Get video number of frames per second; useful to handle slow motion videos
#             for i in range(5):
#                 try:
#                     # Try to find video on i-nth track
#                     currentIncarnation['tags']['framerate']=currentIncarnation['meta']['streams'][i]['avg_frame_rate']
#                     currentIncarnation['tags']['framerate']=currentIncarnation['tags']['framerate'].split('/')
#                     currentIncarnation['tags']['framerate']=int(currentIncarnation['tags']['framerate'][0])/int(currentIncarnation['tags']['framerate'][1])
#
#                     # If we reached this point, everything was good and we found a valid framerate.
#                     # No need to continue.
#                     break
#                 except ZeroDivisionError:
#                     # Simply continue to next track if video not found on this track
#                     pass

            # Get video duration
#             currentIncarnation['tags']['video_duration']=sum(
#                 x * float(t) for x, t in zip([1, 60, 3600], reversed(currentIncarnation['tags']['video_duration'].replace(' s','').split(":")))
#             )

            if 'newfps' in currentIncarnation['tags']:
                # We are converting high frame rate to 30fps slow motion video
                currentIncarnation['tags']['video_duration']*=(
                    currentIncarnation['tags']['framerate'] /
                    currentIncarnation['tags']['newfps']
                )
            else:
                # if we aren't changing FPS (slowmotion), set it to a default
                currentIncarnation['tags']['newfps']=currentIncarnation['tags']['framerate']




            # Find video rotation
#             try:
#                 currentIncarnation['tags']['video_rotation']=int(currentIncarnation['meta']['streams'][0]['tags']['rotate'])
#             except KeyError:
#                 # OK, no orientation information
#                 pass

            # Find video codec
#             currentIncarnation['tags']['video_codec']=currentIncarnation['meta']['streams'][0]['codec_name']

            # End of information gathering, now use it

            # create a place for temporary files
            currentIncarnation['tmp']={}

            self.logger.debug('{} ({}): fps={}, newfps={}, recDuration={}, vidDuration={}'.format(
                    currentIncarnation['decryptedFileInfo']['decryptedFilePath'],
                    incarnation,
                    currentIncarnation['tags']['framerate'],
                    currentIncarnation['tags']['newfps'],
                    currentIncarnation['tags']['recording_duration'],
                    currentIncarnation['tags']['video_duration']
                )
            )


            #mark BEGIN create subtitles
            # calculate and generate subtitles for all variations, as slow motion, time lapse and regular

            trimmed=abs(
                asset['incarnations']['master']['tags']['video_duration']-
                (currentIncarnation['tags']['video_duration']*
                currentIncarnation['tags']['newfps']/
                currentIncarnation['tags']['framerate'])
            )>0.01

            if trimmed:
                # Video was clipped
                self.logger.warning((
                    "Can't create reliable wall clock subtitles on edited video {}. Substitles are a rough aproximation. Incarnation duration: {}. Master duration: {}"
                    .format(
                        currentIncarnation['backupfile'],
                        currentIncarnation['tags']['video_duration'],
                        asset['incarnations']['master']['tags']['video_duration']
                    )
                ))

                # Use master's time codes, mutation's aren't reliable
                currentIncarnation['subs']=WallclockSubtitles(
                    asset['incarnations']['master']['tags']['creation_local_object'],
                    asset['incarnations']['master']['tags']['recording_duration'],
                    (
                        asset['incarnations']['master']['tags']['video_duration']*
                        currentIncarnation['tags']['framerate']/
                        currentIncarnation['tags']['newfps']
                    ),
                    circa=True
                )
            else:
                # Calculate subtitles and write to file
                currentIncarnation['subs']=WallclockSubtitles(
                    currentIncarnation['tags']['creation_local_object'],
                    currentIncarnation['tags']['recording_duration'],
                    currentIncarnation['tags']['video_duration']
                )

            currentIncarnation['subs'].generate()

            currentIncarnation['tmp']['subtitles']=tempfile.NamedTemporaryFile(suffix='.srt',dir=self.target, delete=False)
            currentIncarnation['tmp']['subtitles'].close()
            currentIncarnation['tmp']['subtitles']=currentIncarnation['tmp']['subtitles'].name
            currentIncarnation['subs'].dumpSRT(currentIncarnation['tmp']['subtitles'])

            #mark END create subtitles




            #mark BEGIN Write tags and metadata to a text file
#             currentIncarnation['tmp']['metadata']=tempfile.NamedTemporaryFile(suffix='.ffmetadata',dir=self.target, delete=False)
#             currentIncarnation['tmp']['metadata'].close()
#             currentIncarnation['tmp']['metadata']=currentIncarnation['tmp']['metadata'].name
#             with open(currentIncarnation['tmp']['metadata'],'w') as metadata:
#                 print(';FFMETADATA1',file=metadata)
#
#                 for tagname in currentIncarnation['meta']['format']['tags']:
#                     print(
#                         "{}={}".format(
#                             tagname,
#                             currentIncarnation['meta']['format']['tags'][tagname]
#                         ),
#                         file=metadata
#                     )
#
#                 tagMap=[
#                     ('Xmp.dc.source', '{dcim_folder}/{original_file}'),
#                     ('Xmp.xmpMM.DocumentID', 'uuid'),
#                     ('Xmp.iptcExt.PersonInImage', 'people_list'),
#                     ('Xmp.xmp.Rating', 'favorited_percent'),
#
#                     ('Xmp.xmpDM.scene', 'location_context'),
#                     ('Xmp.iptcExt.City', 'location_city'),
#                     ('Xmp.iptcExt.CountryCode', 'location_countryCode'),
#                     ('Xmp.iptcExt.CountryName', 'location_country'),
#                     ('Xmp.iptcExt.ProvinceState', 'location_state'),
#                     ('Xmp.iptcExt.Sublocation', 'location_subLocality'),
#                     ('Xmp.iptcExt.WorldRegion', 'location_context'),
#                 ]
#
#                 for m in tagMap:
#                     fileTagName,photoCurationTagName=m[0],m[1]
#                     if len(m)==3:
#                         modifier=m[2]
#                     else:
#                         modifier=None
#
#                     value=None
#                     if '{' in photoCurationTagName:
#                         # Use format()
#                         value=photoCurationTagName.format(**currentIncarnation['tags'])
#                     elif photoCurationTagName in currentIncarnation['tags']:
#                         value=currentIncarnation['tags'][photoCurationTagName]
#
#                     if modifier and 'nooverwrite' in modifier and fileTagName in incarnation['meta']:
#                         # Do not touch this existing exif/xmp/iptc tag
#                         pass
#                     else:
#                         if value:
#                             self.logger.debug('{}: ({}){}'.format(fileTagName,type(value),value))
#                             if modifier and 'list' in modifier:
#                                 value=[value]
#
#                             print("{}={}".format(fileTagName,value),file=metadata)

            #mark END Write tags and metadata to a text file


            #mark BEGIN Iterate until there is no filename collision
            while True:
                # Calculate possible final file name and save it in our tags dict
                currentIncarnation['tags']['filename']=pathlib.Path(
                    self.target,
                    self.filenameTemplate.render(currentIncarnation['tags'])
                )

                # Check if another file with that name exists
                if os.path.exists(currentIncarnation['tags']['filename']):
                    # If exists, increase our collision_index and restart (while True)
                    currentIncarnation['tags']['collision_index'] += 1
                else:
                    # No file name collision !!!!!

                    # Create containing folder, if doesn't exist
                    currentIncarnation['tags']['filename'].parent.mkdir(parents=True, exist_ok=True)
                    break

                if currentIncarnation['tags']['collision_index']>99:
                    # Log file is not viable ignore it and log its name
                    self.logger.warning((
                        'Asset «{}» has more than 100 file name collisions. Giving up on it.'
                        .format(currentIncarnation['tags']['filename'])
                    ))
                    del currentIncarnation['tags']['filename']
                    break
            #mark END Iterate until there is no filename collision





            if 'filename' in currentIncarnation['tags']:
                original  = ffmpeg.input(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])
                subtitles = ffmpeg.input(currentIncarnation['tmp']['subtitles'])
#                 metadata  = ffmpeg.input(currentIncarnation['tmp']['metadata'])


                ffmpegFlags={
                    'metadata:s:s:0': 'title=Wall clock',
                    'tag:s:s:0': 'tx3g',


                    # iOS videos include several track with proprietary data that is
                    # currently unknown, unreadable and thus useless. Including them
                    # on generated file will cause future problems with exiftool tagging.
                    # So this parameters will ignore and eliminate them.
                    'map': '-0:d'

                    # -metadata:s:v rotate="-90"
                }

                if 'video_rotation' in currentIncarnation['tags']:
                    ffmpegFlags['metadata:s:v']='rotate={}'.format(currentIncarnation['tags']['video_rotation'])

                if 'newfps' in currentIncarnation['tags'] and currentIncarnation['tags']['newfps']!=currentIncarnation['tags']['framerate']:
                    # Handle slowmotion video. Turn a 240fps video into a real slowmotion 30fps. Lossless.
                    # This is how to stretch a video track via lossless manipulation of framerate:
                    # ffmpeg -i in.mov -c copy in.264
                    # ffmpeg -r 30 -i in.264 -c copy out.mov


                    currentIncarnation['tmp']['rawvideo']=tempfile.NamedTemporaryFile(
                        suffix='.'+currentIncarnation['tags']['video_codec'],
                        dir=self.target,
                        delete=False
                    )

                    currentIncarnation['tmp']['rawvideo'].close()
                    currentIncarnation['tmp']['rawvideo']=currentIncarnation['tmp']['rawvideo'].name

                    video = original['v:0'].output(
                        currentIncarnation['tmp']['rawvideo'],
                        vcodec='copy'
                    ).run(overwrite_output=True)

                    videoStretched=ffmpeg.input(
                        currentIncarnation['tmp']['rawvideo'],
                        r=currentIncarnation['tags']['newfps']
                    )

                    # This is how to stretch audio:
                    # ffmpeg -i in.mov -filter:a atempo=(30/240) -vn out.m4a

#                     audioStretched = original['a:0'].filter('atempo',
#                         currentIncarnation['tags']['newfps']/currentIncarnation['tags']['framerate']
#                     )

                    # TODO: make this more generic

                    # The ffmpeg atempo filter can slow it down to no less than half the
                    # original speed (0.5), and speed up to no more than double (2.0) the input.
                    # Turning 240fps videos into 30fps requires audio 8 times slower.
                    # In other words we need audio to play 30/240(=0.125) times slower, in contrast
                    # to ffmpeg 0.5 times slower limitation. So we need to find X and T
                    # where T is integer and X is a little bit bigger than 0.5.
                    # Generically speaking: X^T=NFPS/FPS (e.g. X^T=30/240 or X^T=30/120)
                    #
                    # T=math.ceil(math.log(nfps/fps,0.5))
                    # X=(nfps/fps)^(1/T)
                    # Implementation:

                    howMuchSlower=currentIncarnation['tags']['newfps']/currentIncarnation['tags']['framerate']
                    T=math.ceil(math.log(howMuchSlower,0.5))
                    X=math.pow(howMuchSlower,(1/T))

                    audioStretched = original['a:0']

                    for _ in range(T):
                        # Chain multiple atempo filters to overcome its limitations
                        audioStretched = audioStretched.filter('atempo',X)


                    # TODO don't do ALAC
                    muxer=ffmpeg.output(
#                             metadata,
                            videoStretched,
                            audioStretched,
                            subtitles,
                            str(currentIncarnation['tags']['filename']),
                            acodec='alac',
#                             audio_bitrate=160,
                            vcodec='copy',
                            scodec='mov_text',
                            movflags='faststart+use_metadata_tags',
#                             movflags='faststart',
                            map_metadata=0,
                            **ffmpegFlags
                    )
                else:
                    muxer=ffmpeg.output(
#                             metadata,
                            original,
                            subtitles,
                            str(currentIncarnation['tags']['filename']),
                            acodec='copy',
                            vcodec='copy',
                            scodec='mov_text',
                            movflags='faststart+use_metadata_tags',
#                             movflags='faststart',
                            map_metadata=0,
                            **ffmpegFlags
                    )

                muxer=muxer.global_args('-hide_banner')

                # Document the entire ffmpeg muxer command as a tag
                currentIncarnation['tags']['muxer']="'" + "' '".join(muxer.compile()) + "'"

                try:
                    self.logger.debug('"' + '" "'.join(muxer.compile()) + '"')
#                     PhotoCuration.myMuxerRun(muxer)
                    muxer.run()
                except Exception as e:
                    self.logger.error(currentIncarnation['subs'])
                    raise e

                del subtitles

                #mark BEGIN old fashion tagging
#                 currentIncarnation['meta']=mutagen.File(str(currentIncarnation['tags']['filename']))
#                 self.tagVideo(currentIncarnation)
                #mark END old fashion tagging

                self.tagger.tag(currentIncarnation, sourceMedia=currentIncarnation['decryptedFileInfo']['decryptedFilePath'])

        #mark END iterate over all incarnations

        #mark BEGIN general cleanup

        for incarnation in asset['incarnations']:
            currentIncarnation=asset['incarnations'][incarnation]

            try:
                os.remove(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])
            except (FileNotFoundError,KeyError):
                # File was not tracked or was deleted by a previous incarnation cleanup
                pass

            if 'tmp' in currentIncarnation:
                self.logger.debug("Cleanup: " + str(currentIncarnation['tmp']))
                for i in currentIncarnation['tmp']:
                    os.remove(currentIncarnation['tmp'][i])

        #mark END general cleanup



    def myMuxerRun(
        stream_spec,
        cmd='ffmpeg',
        capture_stdout=False,
        capture_stderr=False,
        input=None,
        quiet=False,
        overwrite_output=False,
    ):

        pipe_stdin=False
        pipe_stdout=False
        pipe_stderr=False
        quiet=False

        args = stream_spec.compile(cmd, overwrite_output=overwrite_output)


        # I'm rewriting ffmpeg's run and run_async functions just to remove 2
        # arguments ('-map' '0') in the following block:
        for i in range(len(args)):
            if str(args[i])=='0' and args[i-1]=='-map':
                break
        if i<len(args)-1:
            del args[i-1:i+1]



        stdin_stream = subprocess.PIPE if pipe_stdin else None
        stdout_stream = subprocess.PIPE if pipe_stdout else None
        stderr_stream = subprocess.PIPE if pipe_stderr else None
        if quiet:
            stderr_stream = subprocess.STDOUT
            stdout_stream = subprocess.DEVNULL
        process=subprocess.Popen(
            args, stdin=stdin_stream, stdout=stdout_stream, stderr=stderr_stream
        )

        out, err = process.communicate(input)
        retcode = process.poll()
        if retcode:
            raise Exception('ffmpeg', out, err)
        return out, err





    def tagVideo(self, incarnation):
        tagMap=[
            ('\xa9nam', 'suggested_caption'),
            ('desc', 'suggested_caption'),
            ('\xa9too', 'app_creator'),
            ('\xa9alb','keywords'),
            ('\xa9ART','device_owner'),
            ('\xa9grp','keywords'),
            ('rtng','favorited_percent'),

            ('----::com.apple.quicktime.creationdate', 'tag_creation_date'), # =2020-11-07T16:42:21-0300
            ('----::com.apple.quicktime.make', 'camera_make'), #=Apple
            ('----::com.apple.quicktime.model', 'camera_model'), #=iPhone 11 Pro
            ('----::com.apple.quicktime.software', 'camera_software_version'), #=14.1
            ('----::com.apple.quicktime.location.accuracy.horizontal', 'location_accuracy_horizontal'), #=65.000000
            ('----::com.apple.quicktime.location.ISO6709', 'location_ISO6709'), #=-23.5506-046.6835+792.764/


            ('----:Xmp.dc:source', '{dcim_folder}/{original_file}'),
            ('----:Xmp.xmpMM:DocumentID', 'uuid'),
            ('----:Xmp.iptcExt:PersonInImage', 'people_list'),
            ('----:Xmp.xmp:Rating', 'favorited_percent', 'list'),

            ('----:Xmp.xmpDM:scene', 'location_context'),
            ('----:Xmp.iptcExt:City', 'location_city'),
            ('----:Xmp.iptcExt:CountryCode', 'location_countryCode'),
            ('----:Xmp.iptcExt:CountryName', 'location_country'),
            ('----:Xmp.iptcExt:ProvinceState', 'location_state'),
            ('----:Xmp.iptcExt:Sublocation', 'location_subLocality'),
            ('----:Xmp.iptcExt:WorldRegion', 'location_context')
        ]


        ffmetadata="""
;FFMETADATA1
major_brand=M4V
compatible_brands=M4V mp42isom
minor_version=0
rating=1
title=Bitch I'm Madonna
artist=Madonna
composer=Ariel Rechtshaid
album=Bitch I'm Madonna
genre=Pop
track=1/1
disc=1/1
date=2014-12-22
compilation=0
gapless_playback=0
MusicBrainz Album Release Country=FR
LANGUAGE=eng
SCRIPT=Latn
MusicBrainz Album Type=single
ARTISTS=Madonna
MusicBrainz Album Status=official
ISRC=USUG11401961
CATALOGNUMBER=0060254720174
MEDIA=Digital Media
WORK=Bitch I'm Madonna
PRODUCER=SOPHIE
MusicBrainz Release Group Id=2d98fffb-ce9e-4652-ae2a-6a98bdb5306b
MusicBrainz Work Id=2ee5508f-a3e1-44b9-bb28-aa7824dab23c
MusicBrainz Album Id=3116df3a-ccd8-4e52-8c74-d14d1e09bdd1
MusicBrainz Track Id=39543c56-a386-46c2-a4eb-e9ec77749d24
MusicBrainz Release Track Id=58faf347-bcf6-4116-b407-38c9cac05eda
MusicBrainz Artist Id=79239441-bfd5-4981-a70c-55c3f15c1287
MusicBrainz Album Artist Id=79239441-bfd5-4981-a70c-55c3f15c1287
iTunEXTC=||0|
iTunMOVI=<?xml version\="1.0" encoding\="UTF-8"?>\
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\
<plist version\="1.0">\
<dict>\
	<key>asset-info</key>\
	<dict>\
		<key>file-size</key>\
		<integer>48343373</integer>\
		<key>flavor</key>\
		<string>6:640x480LC-256</string>\
		<key>screen-format</key>\
		<string>widescreen</string>\
	</dict>\
</dict>\
</plist>\

sort_album_artist=Madonna
sort_artist=Madonna
album_artist=Madonna
purchase_date=2015-07-23 14:40:53
account_id=iTunes Store
sort_name=Bitch I'm Madonna (feat. Nicki Minaj)
copyright=© (P) 2015 Boy Toy, Inc., Exclusively licensed to Live Nation Worldwide, Inc.  Exclusively licensed to Interscope Records
media_type=6
encoder=Lavf58.45.100
minor_version=0
com.apple.quicktime.creationdate=2020-11-06T08:50:03-0300
com.apple.quicktime.location.accuracy.horizontal=65.000000
com.apple.quicktime.live-photo.auto=1
com.apple.quicktime.content.identifier=F890905C-846E-41BB-8C50-8D7A873E9136
com.apple.quicktime.live-photo.vitality-score=1.000000
com.apple.quicktime.live-photo.vitality-scoring-version=0
com.apple.quicktime.location.ISO6709=-23.5399-046.6565+766.849/
com.apple.quicktime.make=Apple
com.apple.quicktime.model=iPhone 11 Pro
com.apple.quicktime.software=14.1
encoder=Lavf58.45.100
Some random tag by Avi Alkalay with 🙂 emoji=coisa linda
        """

        if incarnation['meta'].tags is None:
            incarnation['meta'].add_tags()

        for m in tagMap:
            fileTagName,photoCurationTagName=m[0],m[1]
            if len(m)==3:
                modifier=m[2]
            else:
                modifier=None

            value=None
            if '{' in photoCurationTagName:
                # Use format()
                value=photoCurationTagName.format(**incarnation['tags'])
            elif photoCurationTagName in incarnation['tags']:
                value=incarnation['tags'][photoCurationTagName]

            if modifier and 'nooverwrite' in modifier and fileTagName in incarnation['meta']:
                # Do not touch this existing exif/xmp/iptc tag
                pass
            else:
                if value:
                    self.logger.debug('{}: ({}){}'.format(fileTagName,type(value),value))
                    if modifier and 'list' in modifier:
                        value=[value]

                    if fileTagName.startswith('----:'):
                        value=value.encode("utf-8")

                    incarnation['meta'].tags[fileTagName]=value

        incarnation['meta'].save()








    def handleImage(self, asset):
        #mark BEGIN read original image and tags/metadata
        currentIncarnation = asset['incarnations']['master']

        currentIncarnation['backupfile']=self.original.format(
            dcim_folder=currentIncarnation['tags']['dcim_folder'],
            file=currentIncarnation['tags']['original_file']
        )

        currentIncarnation['decryptedFileInfo']=self.ios.getFileDecryptedCopy(
            relativePath=currentIncarnation['backupfile'],
            targetFolder=tempfile.gettempdir()
        )

        #mark BEGIN extract image tags (EXIF, etc)
#         metaToTags=[
#             # pyexiv2 bindings
#             ('camera_make', 'Exif.Image.Make'),
#             ('camera_model', 'Exif.Image.Model'),
#             ('camera_lens_make', 'Exif.Photo.LensMake'),
#             ('camera_lens_model', 'Exif.Photo.LensModel'),
#             ('camera_software_version', 'Exif.Image.Software'),
#
#             # exifread bindings
#             ('camera_make', 'Image Make'),
#             ('camera_model', 'Image Model'),
#             ('camera_lens_make', 'EXIF LensMake'),
#             ('camera_lens_model', 'EXIF LensModel'),
#             ('camera_software_version', 'Image Software')
#         ]


        # Try multiple libraries to get file photo tags
#         try:
#             # Try first with the Py3Exiv2 library. Linux only, write support, no HEIF yet.
#             currentIncarnation['meta'] = pyexiv2.ImageMetadata(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])
#             currentIncarnation['meta'].read()
#         except:
#             # Try with Exifread library. All platforms, read only, HEIF support.
#             with open(currentIncarnation['decryptedFileInfo']['decryptedFilePath'],'rb') as heif:
#                 currentIncarnation['meta']=exifread.process_file(heif)

        #mark END extract image tags (EXIF, etc)

        currentIncarnation['tags'].update(
            self.tagger.getTags(
                currentIncarnation['decryptedFileInfo']['decryptedFilePath']
            )
        )

        # Update the tags dict with photo tags extracted from file
#         for varname,tagname in metaToTags:
#             try:
#                 # Try first with the Py3Exiv2 library.
#                 currentIncarnation['tags'][varname]=currentIncarnation['meta'][tagname].value
#             except AttributeError:
#                 # Try with Exifread library (value×values attribute).
#                 currentIncarnation['tags'][varname]=currentIncarnation['meta'][tagname].values
#             except KeyError:
#                 # Exif tag unavailable in image, so ignore it.
#                 pass



        #mark END read original image and tags/metadata



        #mark BEGIN decisions about originals
        if asset['incarnations']['master']['tags']['edited']:
#               original='Media/{dcim_folder}/{file}'
#               mutation='Media/PhotoData/Mutations/{dcim_folder}/{file_no_extension}/Adjustments/FullSizeRender.{file_extension}'

            if (type(self.originals) is bool and self.originals) or (type(self.originals) is list and asset['incarnations']['master']['tags']['kind_encoded'] in self.originals):
                # Create an incarnation for the original based on the master and mark it as unedited
                asset['incarnations']['original']=copy.deepcopy(asset['incarnations']['master'])
                asset['incarnations']['original']['tags']['unedited']=True

            # Create the main incarnation
            asset['incarnations']['main']=copy.deepcopy(asset['incarnations']['master'])

            asset['incarnations']['main']['backupfile']=self.mutation.format(
                dcim_folder=asset['incarnations']['main']['tags']['dcim_folder'],
                file_no_extension=asset['incarnations']['main']['tags']['original_file_no_extension'],
                file_extension=asset['incarnations']['main']['tags']['original_file_extension'],
            )
        else:
            # The 'main' incarnation is the original file
            asset['incarnations']['main']=copy.deepcopy(asset['incarnations']['master'])

        #mark END decisions about originals

        # At this point we have all incarnations that we desire, mostly 'main' and 'original'


        #mark BEGIN itarate over incarnations
        for incarnation in asset['incarnations']:
            if 'master' in incarnation:
                # 'master' is not a real incarnation we have to handle, so skip it
                continue

            currentIncarnation=asset['incarnations'][incarnation]



            # Extract image from iOS backup and put it into target folder with a temporary name
            try:
                # FIXME: bad place for this decision
                currentIncarnation['decryptedFileInfo']=self.ios.getFileDecryptedCopy(
                    targetFolder=self.target,
                    relativePath=currentIncarnation['backupfile']
                )
            except FileNotFoundError:
                # Error probably because edited [HEIC|PNG|DNG|CR2] became JPG
                currentIncarnation['decryptedFileInfo']=self.ios.getFileDecryptedCopy(
                    targetFolder=self.target,
                    relativePath=(
                        currentIncarnation['backupfile']
                        .replace('.png','.jpg')
                        .replace('.heic','.jpg')
                        .replace('.jpeg','.jpg')
                        .replace('.dng','.jpg')
                        .replace('.cr2','.jpg')
                    )
                )


            currentIncarnation['tags']['ext'] = os.path.splitext(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])[1][1:].strip().lower()



            #mark BEGIN find and avoid file name clashes

            # Iterate until there is no filename collision
            while True:
                # Calculate possible final file name and save it in our tags dict
                currentIncarnation['tags']['filename']=pathlib.Path(
                    self.target,
                    self.filenameTemplate.render(currentIncarnation['tags'])
                )

                # Check if another file with that name exists
                if os.path.exists(currentIncarnation['tags']['filename']):
                    # If exists, increase our collision_index and restart (while True)
                    currentIncarnation['tags']['collision_index'] += 1
                else:
                    # No file name collision !!!!!

                    # Create containing folder, if doesn't exist
                    currentIncarnation['tags']['filename'].parent.mkdir(parents=True, exist_ok=True)

                    # Rename temporary file to final filename
                    os.rename(
                        currentIncarnation['decryptedFileInfo']['decryptedFilePath'],
                        currentIncarnation['tags']['filename']
                    )
                    break

                if currentIncarnation['tags']['collision_index']>99:
                    # Log file is not viable ignore it and log its name
                    logging.warning('Asset «{}» has more than 100 file name collisions. Giving up on it.'.format(currentIncarnation['tags']['filename']))
                    break

            #mark END find and avoid file name clashes


            # Now tag file with exiftool
            self.tagger.tag(currentIncarnation, sourceMedia=asset['incarnations']['master']['decryptedFileInfo']['decryptedFilePath'])

#             # Set filesystem time as create time
#             mtime=time.mktime(info['lastModified'].astimezone(tz=None).timetuple())
#             os.utime(targetFileName,(mtime, mtime))

        #mark END itarate over incarnations



        #mark BEGIN cleanup

        # Remove original file used as a base for tags
        os.remove(asset['incarnations']['master']['decryptedFileInfo']['decryptedFilePath'])

        #mark END cleanup


    def tagImage(self, incarnation):
        tagMap=[

            ('Exif.Image.DocumentName', '{dcim_folder}/{original_file}'),
#             ('Xmp.plus.FileNameAsDelivered', '{filename}'),
            ('Exif.Image.ImageDescription', 'suggested_caption'),
            ('Exif.Image.Software', 'app_creator_or_editor', 'nooverwrite'),
            ('Exif.Image.HostComputer', 'Extracted from {device_hostname} running iOS {device_ios_version} build {device_ios_build}'),
            ('Exif.Image.Rating', 'favorited_5stars'),
            ('Exif.Image.RatingPercent', 'favorited_percent'),
            ('Exif.Image.ImageID', '{dcim_folder}/{original_file}'),






            ('Exif.Image.CameraSerialNumber', 'device_serial_number'),


            ('Exif.Photo.UserComment', 'suggested_caption'),
            ('Exif.Photo.CameraOwnerName', 'device_owner'),
            ('Exif.GPSInfo.GPSAreaInformation', 'location_context'),

            ('Iptc.Application2.LocationName', 'location_suggested_name', 'list'),

            ('Iptc.Application2.City', 'location_city', 'list'),
            ('Iptc.Application2.SubLocation', 'location_subLocality', 'list'),
            ('Iptc.Application2.ProvinceState', 'location_state', 'list'),
            ('Iptc.Application2.CountryCode', 'location_countryCode', 'list'),
            ('Iptc.Application2.CountryName', 'location_country', 'list'),
            ('Iptc.Application2.Credit', 'author', 'list'),
            ('Iptc.Application2.Caption', 'suggested_caption', 'list'),
            ('Xmp.dc.creator', 'author', 'list'),
            ('Xmp.dc.description', 'suggested_caption'),
            ('Xmp.dc.source', '{dcim_folder}/{original_file}'),
            ('Xmp.dc.subject', 'keywords'),
            ('Xmp.dc.title', 'suggested_caption'),
            ('Xmp.xmp.CreatorTool', 'app_creator'),
#             ('Xmp.xmp.Nickname', '{dcim_folder}/{original_file}'),
            ('Xmp.xmp.Rating', 'favorited_percent'),
            ('Xmp.xmpRights.Owner', 'device_owner', 'list'),

            ('Xmp.xmpMM.DocumentID', 'uuid'),

            ('Xmp.xmpDM.shotLocation', 'location_suggested_name'),
            ('Xmp.photoshop.Country', 'location_country'),
            ('Xmp.photoshop.State', 'location_state'),
            ('Xmp.photoshop.City', 'location_city'),


            ('Xmp.dc.identifier', 'uuid'),

            ('Xmp.xmpDM.album', '{albums_list}'),
            ('Xmp.xmpDM.artist', 'author'),

            ('Xmp.xmpDM.scene', 'location_context'),
            ('Xmp.iptcExt.PersonInImage', 'people_list'),


            ('Xmp.iptcExt.City', 'location_city'),
            ('Xmp.iptcExt.CountryCode', 'location_countryCode'),
            ('Xmp.iptcExt.CountryName', 'location_country'),
            ('Xmp.iptcExt.ProvinceState', 'location_state'),
            ('Xmp.iptcExt.Sublocation', 'location_subLocality'),
            ('Xmp.iptcExt.WorldRegion', 'location_context'),













            ('Xmp.MicrosoftPhoto.CameraSerialNumber', 'device_serial_number'),


            ('Xmp.MicrosoftPhoto.LensManufacturer', 'camera_lens_make', 'nooverwrite'),
            ('Xmp.MicrosoftPhoto.LensModel', 'camera_lens_model', 'nooverwrite'),
            ('Xmp.MicrosoftPhoto.Rating', '{favorited_5stars}'),
            ('Xmp.MicrosoftPhoto.LastKeywordXMP', 'keywords'),



        ]

        for m in tagMap:
            exifTagName,photoCurationTagName=m[0],m[1]
            if len(m)==3:
                modifier=m[2]
            else:
                modifier=None

            value=None
            if '{' in photoCurationTagName:
                # Use format()
                value=photoCurationTagName.format(**incarnation['tags'])
            elif photoCurationTagName in incarnation['tags']:
                value=incarnation['tags'][photoCurationTagName]

            try:
                if modifier and 'nooverwrite' in modifier and exifTagName in incarnation['meta']:
                    # Do not touch this existing exif/xmp/iptc tag
                    pass
                else:
                    if value:
                        if modifier and 'ucs2' in modifier:
                            value=value.encode('utf16')
                        if modifier and 'list' in modifier:
                            value=[value]

                        if 'Xmp' in exifTagName:
                            tag=pyexiv2.XmpTag(exifTagName,value)
                        elif 'Exif' in exifTagName:
                            tag=pyexiv2.ExifTag(exifTagName,value)
                        elif 'Iptc' in exifTagName:
                            try:
                                incarnation['meta'].iptc_charset = 'utf-8'
                            except AttributeError:
                                # We get this error in case of HEIC, just ignore
                                pass
                            tag=pyexiv2.IptcTag(exifTagName,value)

                        incarnation['meta'][exifTagName]=tag


            except Exception as e:
                logging.error("«{}»: «{}» ({})".format(exifTagName,value,type(value)))
                raise e


        if incarnation['people']:
            t='Xmp.dwc.Record/dcterms:bibliographicCitation'
            tag=pyexiv2.XmpTag(t,json.dumps(incarnation['people'],indent=4,ensure_ascii=False))
            incarnation['meta'][t]=tag


        #mark BEGIN handle regions and people faces
#         regions=[]
#         regionListParent='Xmp.mwg-rs.Regions/mwg-rs:RegionList[{}]'
#         keys={
#             'x':    regionListParent + '/mwg-rs:Area/stArea:x',
#             'y':    regionListParent + '/mwg-rs:Area/stArea:y',
#             'w':    regionListParent + '/mwg-rs:Area/stArea:w',
#             'h':    regionListParent + '/mwg-rs:Area/stArea:h',
#             'unit': regionListParent + '/mwg-rs:Area/stArea:unit',
#             'type': regionListParent + '/mwg-rs:Type',
#             'name': regionListParent + '/mwg-rs:Name'
#         }
#
#         if 'Xmp.mwg-rs.Regions' in incarnation['meta']:
#             # We already have Regions here.
#             # Lets extract and put them in an easy structure.
#             i=0
#             while True:
#                 i+=1
#                 if regionListParent.format(i) in incarnation['meta']:
#                     region={'index': i}
#                     for k in keys:
#                         region[k]=incarnation['meta'][keys[k].format(i)]
#                     regions.append(region)
#                 else:
#                     # End of RegionList
#                     break
#
#         if incarnation['people'] and len(incarnation['people'])>0:
#             # This is the complete overwrite mode, person by person
# #             try:
# #                 seq=incarnation['meta'][regionListParent]
# #             except KeyError:
# #                 xmpTag=pyexiv2.xmp.XmpTag(regionListParent, [""])
# #                 incarnation['meta'][regionListParent]=xmpTag
#
#             for pi in range(len(incarnation['people'])):
#                 for k in keys:
#                     xmpTag=keys[k].format(pi+1)
#
#                     self.logger.warning("Creating tag {}={}".format(
#                         xmpTag,
#                         incarnation['people'][pi][k]
#                     ))
#
#                     incarnation['meta'][xmpTag]=pyexiv2.xmp.XmpTag(xmpTag, incarnation['people'][pi][k])

        #mark END handle regions and people faces







        # Write all tags back to image
        if type(incarnation['meta']) is pyexiv2.metadata.ImageMetadata:
            # Write back only if we are using a module capable of writing
            incarnation['meta'].write()




    def itemizeDatetime(df, col, prefix):
        items=[
            #   %format or element,      tag suffix
            ('%Y.%m.%d-%H.%M.%S',      'time_fs'),
            ('%Y-%m-%dT%H:%M:%S.%f%z', 'time_ISO8601'),
            ('%Y:%m:%d %H:%M:%S',      'time_exiftool'),
            ('z',                      'tz_offset'),
            ('Y',                      'year'),
            ('m',                      'month'),
            ('d',                      'day'),
            ('H',                      'hour'),
            ('M',                      'minute'),
            ('S',                      'second'),
            ('f',                      'microsecond'),
            ('y',                      'year_small'),
            ('I',                      'hour12'),
            ('p',                      'ampm'),
            ('b',                      'month_name_abrev'),
            ('B',                      'month_name'),
            ('a',                      'weekday_abrev'),
            ('A',                      'weekday'),
            ('c',                      'locale_time') # Tue Aug 16 21:30:00 1988
        ]

        for i in items:
            df[f'{prefix}_{i[1]}']=df[col].apply(
                func=lambda x: x.strftime(
                    i[0] if '%' in i[0] else f'%{i[0]}'
                )
            )

        # Custom items

        df[f'{prefix}_time_exiftool']=df.apply(
            axis=1,
            func=lambda x: '{}.{:.2}{}:{}'.format(
                x[f'{prefix}_time_exiftool'],
                x[f'{prefix}_microsecond'],
                x[f'{prefix}_tz_offset'][:3],
                x[f'{prefix}_tz_offset'][3:5]
            ),
        )



    def fetchPeople(self):
        self.peopleOfAssets=pd.read_sql_query(
            self.facesForAssets,
            con=self.db
        )

        self.peopleOfAssets=self.peopleOfAssets.convert_dtypes()



    def fetchPlacesMoments(self):
        generalDateFormat='%Y-%m-%d %H:%M:%S'
        dateformat={
            'moment_utc_start': generalDateFormat,
            'moment_utc_end': generalDateFormat,
            'moment_momenttime_start': generalDateFormat,
            'moment_momenttime_end': generalDateFormat,
            'asset_utc_created': generalDateFormat,
            'asset_assettime_created': generalDateFormat
        }

        self.assetsOfPlaces=pd.read_sql_query(
            self.assetsForMoments,
            parse_dates=dateformat,
            con=self.db
        )
        self.assetsOfPlaces=self.assetsOfPlaces.convert_dtypes()





    def fetchMemories(self):
        memoryMetadataFolder='Media/PhotoData/AlbumsMetadata'
        dateformat={
            'memory_utc_creation': '%Y-%m-%d %H:%M:%S',
        }


        self.memories=pd.read_sql_query(
            self.listOfMemories,
            index_col='memory_pk',
            parse_dates=dateformat,
            con=self.db
        )
#         self.memories=self.memories.convert_dtypes() # optimize data types

#         datetimeCols=['album_utc_creation','album_utc_start','album_utc_end']

#         for c in datetimeCols:
#             self.albums[c]=pd.to_datetime(self.albums[c], utc=True)

        assets=[]
        for index, memory in self.memories.iterrows():
            # print(memory)

            if memory['ZMOVIEASSETSTATE'] != b'None' and memory['ZMOVIEASSETSTATE'] != None:
                try:
                    struct=NSKeyedUnArchiver.unserializeNSKeyedArchiver(memory['ZMOVIEASSETSTATE'])
                except:
                    print("{}: Invalid plist".format(memory['memory_title']))
                    continue

                for i in struct.keys():
                    assets.append({
                        'memory': index,
                        'memoryUUID': memory['memory_uuid'],
#                         'memoryTrashed': memory['memory_is_trashed'],
                        'assetUUID': i
                    })
                # print(assets)

        if len(assets)>0:
            self.assetsOfMemories=pd.DataFrame(assets)
            del assets
            self.assetsOfMemories=self.assetsOfMemories.convert_dtypes()
            self.assetsOfMemories=self.assetsOfMemories.join(
                self.assetsOfMemories['memory'].value_counts(),
                on='memory',
                rsuffix='_asset_count'
            )



    def fetchAlbums(self):
        albumMetadataFolder='Media/PhotoData/AlbumsMetadata'
        dateformat={
            'album_utc_creation': '%Y-%m-%d %H:%M:%S',
            'album_utc_start': '%Y-%m-%d %H:%M:%S',
            'album_utc_end': '%Y-%m-%d %H:%M:%S',
        }


        self.albums=pd.read_sql_query(
            self.listOfAlbums,
            index_col='album_pk',
            parse_dates=dateformat,
            con=self.db
        )
        self.albums=self.albums.convert_dtypes()[(self.albums['album_is_trashed']==0) & (self.albums['album_asset_count']>0)]
#         self.albums=self.albums[(self.albums['album_is_trashed']==0) & (self.albums['album_asset_count']>0)]

#         datetimeCols=['album_utc_creation','album_utc_start','album_utc_end']

#         for c in datetimeCols:
#             self.albums[c]=pd.to_datetime(self.albums[c], utc=True)

        assets=[]
        for index, album in self.albums.iterrows():
            try:
                (info,data)=self.ios.getRelativePathDecryptedData(
                    relativePath=os.path.join(
                        albumMetadataFolder,
                        album['album_uuid'] + ".albummetadata")
                )
            except FileNotFoundError:
                continue

            struct=NSKeyedUnArchiver.unserializeNSKeyedArchiver(data)
            packedAssetUUIDs=struct['assetUUIDs']

            assetCount=int(len(packedAssetUUIDs)/16)
            for i in range(assetCount):
                assets.append({
                    'album': index,
                    'albumUUID': album['album_uuid'],
                    'albumTrashed': album['album_is_trashed'],
                    'assetUUID': str(uuid.UUID(bytes=packedAssetUUIDs[i*16:(i+1)*16])).upper()
                })

        self.assetsOfAlbums=pd.DataFrame(assets)
        self.assetsOfAlbums=self.assetsOfAlbums.convert_dtypes()

        del assets

        # Compute album textual date range as ISO 8601:
        #
        # 2022-02-03 -- all assets in a single day
        # 2022-02-03/06 -- assets between Feb 3 and 6
        # 2022-02-27/03-06 -- assets between Feb 27 and Mar 6
        # 2021-12-26/2022-01-10 -- assets between those 2 dates
        #
        # Reference: https://en.wikipedia.org/wiki/ISO_8601#Time_intervals

        # Summary of next Pandas-one-liner big block:
        #
        # 0. Select only non-trashed assets
        # 1. Get list of assets and start and end (videos) localtime
        # 2. Pair them with their albums
        # 3. Group by album to get album start and end localtime
        # 4. Eliminate empty albums
        # 5. Compute period string (ex: "2022-02-27/03-06")
        # 5.1 Compute end date in an appropriate format
        # 6. Pair album period string to its album
        # 7. Put period string in 'album_period' column

        # Now the one-liner:
        # 7. Put period string in 'album_period' column
        self.albums['album_period']=(
            # 6. Pair album period string to its album
            self.albums.join(
                # 2. Pair them with their albums
                self.assetsOfAlbums.join(
                    # 0. Select only non-trashed assets
                    # self.assets[self.assets.trashed<(2 if self.trashed else 1)]
                    self.assets
                    # 1. Get list of assets and start and end (videos) localtime
                    .apply(
                        axis=1,
                        result_type='expand',
                        func=lambda w: dict(
                            assetUUID=w['uuid'],
                            album_local_start=(
                                w['utc_time'].tz_convert(pytz.FixedOffset(w['tz_offset']/60))
                            ),
                            album_local_end=(
                                w['utc_time']+pd.Timedelta(seconds=w['video_duration'])
                            ).tz_convert(pytz.FixedOffset(w['tz_offset']/60)),
                        )
                    )
                    .set_index('assetUUID'),
                    on='assetUUID',
                    how='right'
                )
                # 3. Group by album to get album start and end localtime
                .groupby(by='albumUUID').agg(
                    dict(
                        album_local_start='min',
                        album_local_end='max'
                    )
                ),
                on='album_uuid'
            )
            # 4. Eliminate empty albums
            .dropna(subset=['album_local_start'])
            # 5. Compute period string (ex: "2022-02-27/03-06")
            .apply(
                axis=1,
                result_type='expand',
                func=lambda w: '/'.join([
                    i for i in [
                        w['album_local_start'].strftime('%Y-%m-%d'),
                        # 5.1 Compute end date in an appropriate format
                        w['album_local_end'].strftime('%Y-%m-%d') if w['album_local_start'].year!=w['album_local_end'].year else (
                            w['album_local_end'].strftime('%m-%d') if w['album_local_start'].month!=w['album_local_end'].month else (
                                w['album_local_end'].strftime('%d') if w['album_local_start'].day!=w['album_local_end'].day else None
                            )
                        )
                    ]
                    if i
                ])
            )
        )



    def calcAssetsKeywords(self):
        """
        Add following columns to self.assets:

        albums_list: contains Python list with names of all albums the asset is in.

        memories_list: contains Python list with "title @ subtitle" of all memories the asset is in.

        people_list: contains Python list named of all named people that appear in asset.

        keywords: an emoji-formatted Python list including all the above.
        """

        if hasattr(self,'assetsOfAlbums') and self.assetsOfAlbums is not None:
            albumAggregate=[]
            for asset,albums in self.assetsOfAlbums[self.assetsOfAlbums['albumTrashed']==0].join(self.albums, on='album')[['assetUUID','album_title']].groupby('assetUUID'):
                a=albums['album_title'].dropna()
                if a.size>0:
                    albumsOfAasset={
                        'asset_pk': asset,
                        'albums_list': list(a),
                    }
                    albumAggregate.append(albumsOfAasset)

            self.assets=self.assets.join(
                pd.DataFrame(albumAggregate).set_index('asset_pk'),
                on='uuid'
            )


        if hasattr(self,'assetsOfMemories') and self.assetsOfMemories is not None:
            memoryAggregate=[]
            for asset,memories in self.assetsOfMemories.join(self.memories[self.memories['trashed']==0], on='memory')[['assetUUID','memory_title','memory_subtitle']].groupby('assetUUID'):
                memories['memory_title_subtitle']=memories[['memory_title', 'memory_subtitle']].agg(' @ '.join, axis=1)

                memoriesOfAsset={
                    'asset': asset,
                    'memories_list': list(memories['memory_title_subtitle']),
                }
                memoryAggregate.append(memoriesOfAsset)

            self.assets=self.assets.join(
                pd.DataFrame(memoryAggregate).set_index('asset'),
                on='uuid'
            )
        else:
            self.assets['memories_list']=pd.NA


        if hasattr(self,'peopleOfAssets') and self.peopleOfAssets is not None:
            peopleAggregate=[]
            for asset,people in self.peopleOfAssets.groupby('asset'):
                peopleOfAAsset={
                    'asset': asset,
                    'people_list': list(people['full_name']),
                }
                peopleAggregate.append(peopleOfAAsset)

            self.assets=self.assets.join(pd.DataFrame(peopleAggregate).set_index('asset'))

        def reformat(thelist,element_format):
            if type(thelist) in (list,tuple):
                return [element_format.format(e) for e in thelist]
            else:
                return []


        formats=dict(
            albums_list='🖼{}',
            memories_list='📅{}',
            people_list='🙂{}',
        )

        # Create a column with empty lists
        self.assets['keywords']=pd.np.empty((len(self.assets), 0)).tolist()

        # Add keywords
        for k in formats.keys():
            if k in self.assets:
                self.assets['keywords']=(
                    self.assets[k]
                    .where(pd.notnull(self.assets[k]),None)
                    .apply(reformat,args=[formats[k]])
                )



    def getLocationDataFromPlist(self,plistData):
#         loc=NSKeyedUnArchiver.unserializeNSKeyedArchiver(plistData)
        try:
            loc=NSKeyedUnArchiver.unserializeNSKeyedArchiver(plistData)
#             loc=biplist.readPlistFromString(plistData)
        except:
#             print(plistData)
            return None


        location={}

#         mapItem_index=loc['$objects'][loc['$top']['root'].integer]['mapItem'].integer
#         sortedPlaceInfos_index=loc['$objects'][mapItem_index]['sortedPlaceInfos'].integer

        # Find location_name inside the NSKeyedArchiver object
        if loc['isHome']:
            location['location_name']='Home'
        elif len(loc['mapItem']['sortedPlaceInfos']):
#                 place_index=loc['$objects'][sortedPlaceInfos_index]['NS.objects'][0].integer
#                 placeName_index=loc['$objects'][place_index]['name'].integer
#                 location['location_name']=loc['$objects'][placeName_index]
                location['location_name']=loc['mapItem']['sortedPlaceInfos'][0]['name']

        # Find location_context inside the NSKeyedArchiver object
        place=[ p['name'] for p in loc['mapItem']['sortedPlaceInfos'] ]
#         for l in loc['$objects'][sortedPlaceInfos_index]['NS.objects']:
#             placeName_index=loc['$objects'][l.integer]['name'].integer
#             place.append(loc['$objects'][placeName_index])
        places=set()
        places_add=places.add
        location['location_context']=' ⊂ '.join([x for x in place if not (x in places or places_add(x))])

        mapper={
            # the relationship between my desired keys and the plist keys
            'location_formattedAddress':      '_formattedAddress',
            'location_addressString':         'addressString',
            'location_countryCode':           '_ISOCountryCode',
            'location_country':               '_country',
            'location_postalCode':            '_postalCode',
            'location_state':                 '_state',
            'location_adminArea':             '_subAdministrativeArea',
            'location_subLocality':           '_subLocality',
            'location_city':                  '_city',
            'location_street':                '_street'
        }

        # Find various items inside the NSKeyedArchiver object
#         postalAddress_index=loc['$objects'][loc['$top']['root'].integer]['postalAddress'].integer

        for k in mapper.keys():
            if mapper[k] in loc['postalAddress'] and loc['postalAddress'][mapper[k]] is not None:
                location[k]=loc['postalAddress'][mapper[k]]

#                 if mapper[k] in loc['postalAddress'] and loc['postalAddress'][mapper[k]] is not None:
#                 i=loc['postalAddress'][mapper[k]].integer
# #                 print("{}: {}".format(type(loc['$objects'][i]),loc['$objects'][i]))
#                 if loc['$objects'][i] != '$null':
#                     location[k]=loc['$objects'][i]

        return location


    def calcBestLocationName(self):
        """
        Compute best location name as `location_suggested_name`.

        Try first on `location_name` expecting it to be something like 'Epcot Center'.
        Switch to `moment_title` if `location_name` is a mere street address.
        """

        locationColumns=[
            'location_street',
            'location_subLocality',
            'location_city',
            'location_adminArea',
            'location_state',
            'location_country',
            'location_postalCode',
            'location_countryCode',
        ]

        bestLocations=[]
        for (i,a) in self.assets.iterrows():
            bestSoFar=a['moment_title']
            bestFromLocation=None
            if a['location_name'] is not pd.NA:
                bestFromLocation=a['location_name']
                for locPart in locationColumns:
                    if (a[locPart] is not pd.NA) and (a['location_name']==a[locPart]):
                        # location_name is a street address or state or citi. Discard in favor of moment_title
                        bestFromLocation=None
                        break

            best={
                'index': i,
                'location_suggested_name': bestFromLocation or bestSoFar
            }

            bestLocations.append(best)

        bestLocationName=pd.DataFrame(bestLocations).set_index('index')
        del bestLocations

        self.assets=self.assets.join(bestLocationName)
        del bestLocationName



    def calcBestAssetCaption(self):
        # https://stackoverflow.com/a/36490274/367824
        priority=[
            'caption',
            'album_title',
            'memory_title',
            'location_suggested_name'
        ]

        order=iter(priority)

        col=next(order)
        pos=0
        score=1-pos/len(priority)
        bestCaption=pd.DataFrame()
        bestCaption['infered_asset_caption']=self.assets[col].copy()
        bestCaption['infered_asset_caption_score']=bestCaption['infered_asset_caption'].apply(lambda x: score if not pd.isnull(x) else pd.NA)
        for col in order:
            pos+=1
            score=1-pos/len(priority)
            bestCaption['infered_asset_caption']=bestCaption['infered_asset_caption'].fillna(self.assets[col])
            bestCaption['infered_asset_caption_score']=bestCaption['infered_asset_caption_score'].fillna(self.assets[col].apply(lambda x: score if not pd.isnull(x) else pd.NA))

        self.assets=self.assets.join(bestCaption)




    def fetchAssets(self):
        dateformat={
            'utc_time': '%Y-%m-%d %H:%M:%S',
            'exif_timestamp': '%Y:%m:%d %H:%M:%S',
            'asset_local_time': '%Y-%m-%d %H:%M:%S'
        }

        self.assets=pd.read_sql_query(
            self.listOfAssets,
            index_col='Asset_PK',
            parse_dates=dateformat,
            con=self.db
        )
        # We don't want to convert_dtypes() because it inserts pd.NAs which is bad
        # for Jinja2 templates. We want plain python None or empty strings stuff.
#         self.assets=self.assets.convert_dtypes()
#
#         if self.start: self.assets=self.assets[self.assets['utc_time']>=self.start]
#         if self.end:   self.assets=self.assets[self.assets['utc_time']<=self.end]
#
#         self.assets=self.assets[self.assets['trashed']==0]

        # Remove a '\n' from Moment title that Apple inserts to look nicer in Moment cards
        self.assets['moment_title']=self.assets['moment_title'].str.replace('\xa0',' ')
        self.assets['utc_time']=self.assets['utc_time'].dt.tz_localize('UTC')

        # Do not merge with tz_offset here to not mess with curatedArchiving() start and end filters
#         self.assets['asset_local_time']=self.assets.apply(
#             lambda w: w['asset_local_time'].tz_localize(pytz.FixedOffset(w['tz_offset']/60)),
#             axis=1
#         )

        self.assets['caption']=self.assets['caption'].str.strip()
        self.assets['device_owner']=self.device_owner
        self.assets['device_hostname']=self.ios.manifest['Lockdown']['DeviceName'] # device name or hostname
        self.assets['device_ios_version']=self.ios.manifest['Lockdown']['ProductVersion'] # iOS version as 14.0.1, see Version column of https://en.wikipedia.org/wiki/IOS_version_history#Version_history
        self.assets['device_ios_build']=self.ios.manifest['Lockdown']['BuildVersion'] # iOS version as 18A393, see Build column of https://en.wikipedia.org/wiki/IOS_version_history#Version_history
        self.assets['device_serial_number']=self.ios.manifest['Lockdown']['SerialNumber'] # device serial number
        self.assets['device_product_type']=self.ios.manifest['Lockdown']['ProductType'] # device type as iPhone12,3, see columns Identifier of https://www.theiphonewiki.com/wiki/Models


        # Photo resolved location info lays down in external files, so read
        # all that we are aware of
        locations=[]
        for i,a in self.assets.iterrows():
            l=self.getLocationDataFromPlist(a['location_data'])

            if l:
                l['asset_pk']=i
                locations.append(l)

        # Save it in an additional dataframe
        self.locations=pd.DataFrame(locations)
        self.locations.set_index('asset_pk', inplace=True)
        if 'location_adminArea' not in self.locations:
            self.locations['location_adminArea']=pd.NA
        self.locations=self.locations.convert_dtypes()
        self.locations=self.locations[[
            'location_name',
            'location_context',
            'location_street',
            'location_subLocality',
            'location_city',
            'location_adminArea',
            'location_state',
            'location_country',
            'location_postalCode',
            'location_countryCode',
            'location_formattedAddress'
        ]]
#         self.locations.replace(to_replace='$null', inplace=True)


        # Increment assets dataframe with resolved locations
        self.assets=self.assets.join(self.locations).drop(['location_data'], axis=1)




    def addAssetNameFromSmallestAlbum(self):
        bestMatch=(
            self.assetsOfAlbums
            .set_index('album')
            .join(self.albums)[['album_uuid','album_title','album_asset_count','assetUUID','album_period']]
            .sort_values('album_asset_count')
            .groupby('assetUUID')
            .head(1)
            .set_index('assetUUID')
        )

        self.assets=self.assets.join(bestMatch[['album_title','album_period']], on='uuid')



    def addAssetNameFromSmallestMemory(self):
        if hasattr(self,'assetsOfMemories') and hasattr(self,'memory'):
            bestMatch=(
                self.assetsOfMemories
                .set_index('memory')
                .join(self.memories)[['memory_uuid','memory_title','memory_subtitle','memory_asset_count','assetUUID']]
                .sort_values('memory_asset_count')
                .groupby('assetUUID')
                .head(1)
                .set_index('assetUUID')
            )

            self.assets=self.assets.join(bestMatch[['memory_title','memory_subtitle']], on='uuid')
        else:
            self.assets=self.assets.assign(
                memory_title=None,
                memory_subtitle=None
            )




    def report(self):
        cols=[
            'dcim_folder',
            'original_file',
            'utc_time',
            'tz_offset',
            'asset_local_time',
#             'exif_timestamp',
            'kind_description',
            'trashed',
            'video_duration',
            'infered_asset_caption',
            'location_suggested_name'
        ]

        before=pd.get_option("max_rows")
        pd.set_option("max_rows", None)

        # Assets with low caption score
        badNames=self.assets[(self.assets['infered_asset_caption_score']<0.5) & (self.assets['trashed']==0)][cols]

        display(badNames)




        totalNames=self.assets[(self.assets['trashed']==0)][[
            'dcim_folder',
            'original_file',
            'asset_local_time',
            'kind_description',
            'infered_asset_caption'
        ]]

        display(totalNames)



        pd.set_option("max_rows", before)





    def getPhotoDB(self):
        self.db = sqlite3.connect(self.iosDBs['photos']['decryptedFilePath'])
        return self.db



    def loadConfig(self,configFile=None):
        self.configFile = configFile
        self.config = configparser.ConfigParser()

        if self.configFile==None:
            for plat in self.platformFoldersHint.keys():
                if sys.platform.startswith(plat):
                    self.configFile=os.path.expanduser(self.platformFoldersHint[plat]['config'])

        logging.debug('Config file is {}'.format(os.path.expanduser(os.path.expandvars(self.configFile))))

        self.config.read(os.path.expanduser(os.path.expandvars(self.configFile)))


    def getiOSfiles(self):
        for db in self.iOSfiles:
            self.iosDBs[db]=self.ios.getFileDecryptedCopy(self.iOSfiles[db], temporary=True)
            logging.debug(f"{self.iOSfiles[db]}: {self.iosDBs[db]}")

    def processPhotos(self):
#         nameTemplate='{datetime} {sep} {title} 【{model}】.{ext}'
        mutationFolder=''
        for i,asset in self.assets.iterrows():
            f={}
            f['asset']=i
            f['dcim_folder']=asset['dcim_folder']
            f['file']=asset['file']
            f['file_no_extension']=os.path.splitext(asset['file'])[0]

            print("{asset}, {dcim_folder}/{file}:".format(**f))

            try:
                # First try to see if there is a mutation
#                 print("Trying {}".format(self.mutation.format(**f)))
                file=self.ios.getFileManifestDBEntry(relativePath=self.mutation.format(**f))
            except FileNotFoundError:
                # Then get the main photo
#                 print("Trying {}".format(self.original.format(**f)))
                file=self.ios.getFileManifestDBEntry(relativePath=self.original.format(**f))

            print(file)

    def setAuthor(self, asset):
        """
        Iptc.Application2.Byline: <Iptc.Application2.Byline [String] = ['Avi Alkalay']>
        Xmp.dc.creator: <Xmp.dc.creator [seq ProperName] = ['Avi Alkalay']>
        """

    def setRating(self, asset):
        """
        Xmp.xmp.Rating: <Xmp.xmp.Rating [Closed Choice of Integer] = 5>
        Xmp.MicrosoftPhoto.Rating: <Xmp.MicrosoftPhoto.Rating [Text] = 100>
        """

    def setTitle(self, asset):
        """
        Xmp.dc.title: <Xmp.dc.title [Lang Alt] = {'x-default': 'Dinkenesh (Tati) e Dinkenesh (Lucy), Museu Nacional da Etiópia'}>
        Exif.Image.XPTitle: <Exif.Image.XPTitle [Byte] = 68 0 105 0 110 0 107 0 101 0 110 0 101 0 115 0 104 0 32 0 40 0 84 0 97 0 116 0 105 0 41 0 32 0 101 0 32 0 68 0 105 0 110 0 107 0 101 0 110 0 101 0 115 0 104 0 32 0 40 0 76 0 117 0 99 0 121 0 41 0 44 0 32 0 77 0 117 0 115 0 101 0 117 0 32 0 78 0 97 0 99 0 105 0 111 0 110 0 97 0 108 0 32 0 100 0 97 0 32 0 69 0 116 0 105 0 243 0 112 0 105 0 97 0 0 0>
        """

    def setOriginalFilename(self, asset):
        """
        Xmp.GettyImagesGIFT.OriginalFilename: <Xmp.GettyImagesGIFT.OriginalFilename [] = IMG_3492.JPG>
        XMP:PreservedFileName
        IPTC:ObjectName
        XMP:Title
        XMP:RawFileName

        https://exiftool.org/forum/index.php?topic=10298.0
        """

    def setFaces(self, assets):
        """
        Xmp.mwg-rs.Regions/mwg-rs:RegionList: <Xmp.mwg-rs.Regions/mwg-rs:RegionList [bag RegionStruct] = >
        """




    def sync(self):
        pass




class Tagger:

    keymap={
        'EXIF:Make':                 'camera_make',                       # Apple
        'EXIF:Model':                'camera_model',                      # iPhone 11 Pro
        'EXIF:LensMake':             'camera_lens_make',                  # Apple
        'EXIF:LensModel':            'camera_lens_model',                 # iPhone 11 Pro back dual camera 6mm f/2
        'EXIF:Software':             'camera_software_version',           # 14.1
        'QuickTime:MediaCreateDate': 'media_create_time',         # 2020:11:17 21:18:04 (UTC)
        'QuickTime:CreateDate':      'media_create_time',         # 2020:11:17 21:18:04 (UTC)
        'QuickTime:VideoFrameRate':  'framerate',                  # 30
        'Track1:VideoFrameRate':     'framerate',                  # 30
        'QuickTime:Duration':        'video_duration',               # "27.5 s" or "0:03:02"
        'IFD0:Orientation':          'orientation',
        'Composite:Rotation':        'video_rotation',                  # 90
        'QuickTime:CompressorName':  'video_codec',                # HEVC, H.264
        'Keys:Make':                 'camera_make',
        'Keys:Model':                'camera_model',
        'Keys:Software':             'camera_software_version',
        'QuickTime:Make':            'camera_make',
        'QuickTime:Model':           'camera_model',
        'QuickTime:Software':        'camera_software_version',
        'XMP-iptcExt:ArtworkContentDescription': 'suggested_caption',
    }

    tagMap=[
        # Title, keywords, rating and human curation
        ('XMP-dc:Description',                          'suggested_caption'),
        ('XMP-dc:Title',                                'suggested_caption'),
        ('XMP-iptcExt:ArtworkContentDescription',       'suggested_caption'),
        ('XMP-microsoft:LastKeywordXMP',                'keywords'),
        ('XMP-dc:Subject',                              'keywords'),
        ('XMP-xmpDM:Album',                             '{albums_list}'),
        ('XMP-iptcExt:PersonInImage',                   'people_list'),
        ('XMP-xmp:Rating',                              'favorited_5stars'),
        # ('XMP-microsoft:Rating',                        'favorited_5stars'),
        ('XMP-xmp:RatingPercent',                       'favorited_percent'),

        # Date and time
        # Tags itemized from objects creation_local_object and creation_utc_object
        # ("System:FileModifyDate",                        'creation_local_time_ISO8601'),
        ("System:FileModifyDate",                        'creation_local_time_exiftool'),
        ("XMP-xmp:CreateDate",                           'creation_local_time_exiftool'),
        ("Keys:CreationDate",                            'creation_local_time_exiftool'),
        ("QuickTime:CreateDate",                         'creation_utc_time_exiftool'),

        # Authorship, ownership
        ('XMP-dc:Creator',                              'author', 'list'),
        ('XMP-xmpRights:Owner',                         'device_owner', 'list'),
        ('XMP-xmpDM:Artist',                            'author'),

        # Source IDs
        ('XMP-xmp:CreatorTool',                         'app_creator'),
        ('XMP-xmp:Nickname',                            '{filename}'),
        ('XMP-xmpMM:DocumentID',                        'uuid'),
        ('XMP-dc:Identifier',                           'uuid'),
        ('XMP-dc:Source',                               '{dcim_folder}/{original_file}'),
        ('XMP-microsoft:CameraSerialNumber',            'device_serial_number'),


        # Camera info
        ('XMP-microsoft:LensManufacturer',              'camera_lens_make'),
        ('XMP-microsoft:LensModel',                     'camera_lens_model'),
        ('XMP-getty:CameraMakeModel',                   '{camera_make}/{camera_model}/{camera_software_version}'),
        ('XMP-getty:Composition',                       'muxer'),
        ('XMP-tiff:Make'                                'camera_make',          'nooverwrite'),
        ('XMP-tiff:Model'                               'camera_model',         'nooverwrite'),
        ('XMP-tiff:Software'                            'camera_software_version', 'nooverwrite'),

        # Location data
        ('XMP-xmpDM:ShotLocation',                      'location_suggested_name'),

        ('XMP-iptcExt:LocationCreatedWorldRegion',      'location_context'),
        ('XMP-xmpDM:scene',                             'location_context'),

        ('XMP-iptcExt:LocationCreatedLocationName',     'location_street'),

        ('XMP-iptcExt:LocationCreatedSublocation',      'location_subLocality'),
        ('XMP-iptcExt:LocationCreatedCity',             'location_city'),
        ('XMP-photoshop:City',                          'location_city'),

        ('XMP-iptcExt:LocationCreatedProvinceState',    'location_state'),
        ('XMP-photoshop:State',                         'location_state'),

        ('XMP-iptcExt:LocationCreatedCountryName',      'location_country'),
        ('XMP-iptcCore:CountryCode',                    'location_countryCode'),
        ('XMP-photoshop:Country',                       'location_country'),

        ("Keys:GPSCoordinates",                         '{latitude} {longitude}'),


        # Other
        ('orientation',                                 'orientation'),

        # ffmpeg video rotation (-metadata:s:v rotate="-90") doesn't seem to work
        ('rotation',                                    'video_rotation')
    ]

    faceTemplate=\
        "{{"\
            "Type={f[Type]},"\
            "Name={f[Name]},"\
            "Area={{"\
                "Unit=normalized,"\
                "H={f[Area][h]},"\
                "W={f[Area][w]},"\
                "X={f[Area][x]},"\
                "Y={f[Area][y]}"\
            "}}"\
        "}}"

    def __init__(self):
        self.logger=logging.getLogger('{a}.{b}'.format(a=__name__, b=type(self).__name__))

        self.et=None



    def __del__(self):
        if self.et:
            self.et.terminate()



    def _execute(self,exiftoolParameters):
        import exiftool.exceptions  # pip install PyExifTool
        defaults=['-overwrite_original'] #,'-d','%Y-%m-%dT%H:%M:%S.%f%z']
        exiftoolParameters=defaults+exiftoolParameters

        self.logger.debug(exiftoolParameters)

        # Send all to a running exiftool to finaly tag it
        try:
            self.exiftool().execute(*exiftoolParameters)
            self.logger.debug(f"exiftool command output: {self.exiftool().last_stdout}")
            self.logger.debug(f"exiftool command error: {self.exiftool().last_stderr}")
        except exiftool.exceptions.ExifToolExecuteError as e:
            self.logger.warning(e)



    def exiftool(self):
        if self.et is None:
            import exiftool  # pip install PyExifTool
            self.et=exiftool.ExifToolHelper()

        return self.et



    def getTags(self,file):
        tags=self.exiftool().get_tags(
            tags=['a','G1'] + list(self.keymap.keys()),
            files=file
        )[0]
        self.logger.debug(f"exiftool command output: {self.exiftool().last_stdout}")
        self.logger.debug(f"exiftool command error: {self.exiftool().last_stderr}")
        toReturn={}
        for t in self.keymap:
            if t in tags:
                toReturn[self.keymap[t]]=tags[t]
        return toReturn





    def tag(self, incarnation, sourceMedia=None):
        exiftoolParameters=[]

        # Decide which media file will be used as a base to copy tags.
        # Usually videos need the original video file and images use themselves.
        exiftoolParameters.append('-tagsFromFile')
        if sourceMedia:
            exiftoolParameters.append(sourceMedia)
        else:
            # If no initial media to copy and XMP-convert tags from, use same file that will be tagged
            exiftoolParameters.append('@')
        exiftoolParameters.append("-xmp:all<all")

        # Had to deactivate "-all<all" because it wrongly changes orientation of some selfies
        # exiftoolParameters.append("-all<all")

        # Add file name
        exiftoolParameters.append(str(incarnation['tags']['filename']))

        # Document all as tags:
        incarnation['tags']['tagger']='exiftool ' + ' '.join(exiftoolParameters)

        self.logger.debug(incarnation['tags']['tagger'])

        self._execute(exiftoolParameters)

        # Now that everything was copied, add and edit tags
        exiftoolParameters=[]
        for m in self.tagMap:
            modifier=None
            (xmpTagName,photoCurationTagName) = (m[0],m[1])
            if len(m)==3:
                modifier=m[2]

            value=None
            if '{' in photoCurationTagName:
                try:
                    value=photoCurationTagName.format(**incarnation['tags'])
                except KeyError:
                    pass
            elif photoCurationTagName in incarnation['tags']:
                value=incarnation['tags'][photoCurationTagName]

            if value:
                # nooverwrite & list: keep appending (+=)
                # nooverwrite & regular: check for existence (-=) and add (+=)
                # overwrite & list: reset it first (=''), then add (+=)
                # overwrite & regular: set it

                if modifier and 'nooverwrite' in modifier:
                    # Re-set if value is scalar; keep adding if list
                    if isinstance(value, list):
                        for i in value:
                            exiftoolParameters.append(f'-{xmpTagName}+={i}')
                    else:
                        # this exiftool flag causes tag to be set only if not already set
                        exiftoolParameters.append(f'-{xmpTagName}-=')
                        exiftoolParameters.append(f'-{xmpTagName}+={value}')
                else:
                    if isinstance(value, list):
                        # Overwrite a list implies first cleaning it up
                        exiftoolParameters.append(f'-{xmpTagName}-=')
                        for i in value:
                            # Now add each element of list
                            exiftoolParameters.append(f'-{xmpTagName}+={i}')
                    else:
                        exiftoolParameters.append(f'-{xmpTagName}={value}')

        # Now handle faces and regions after all tags were copied and set, in the exiftool logic
        exiftoolParameters+=self.encodeFaces(incarnation)

        if len(exiftoolParameters):
            exiftoolParameters.append(str(incarnation['tags']['filename']))

            # Document all as tags:
            incarnation['tags']['tagger']='exiftool ' + ' '.join(exiftoolParameters)

            self.logger.debug(incarnation['tags']['tagger'])

            # Send all to a running exiftool to finaly tag it
            self._execute(exiftoolParameters)





    def encodeFaces(self,incarnation):
        """
        Encode faces regions into an exiftool struct
        """

        if incarnation['people']:
            regions=[]

            for f in incarnation['people']:
                # Here we'll first replace all ',' of template into super safe \x1f.
                # Then we make substitutions.
                # Then escape ',' (',' -> '|,').
                # Then convert \x1f into ',' again.

                regions.append(
                    self.faceTemplate
                        .replace(',','\x1f')
                        .format(f=f)
                        .replace(',','|,')
                        .replace('\x1f',',')
                )


            parameters=[]

            # First remove all faces (but keep Focus region)
            parameters.append("-regionlist-={Type=Face}")

            # Add all regions at once
            parameters.append("-regionlist+=[" + ','.join(regions) + "]")

            return parameters
        else:
            # No people to tag
            return []







# class TaggerLibXMP:
#     xmpNamespaces={
#         'xmp':             libxmp.consts.XMP_NS_XMP,
#         'dc':              libxmp.consts.XMP_NS_DC,
#         'exif':            libxmp.consts.XMP_NS_EXIF,
#         'exifEX':          "http://cipa.jp/exif/1.0/",
#         'aux':             libxmp.consts.XMP_NS_EXIF_Aux,
#         'mwg-rs':          'http://www.metadataworkinggroup.com/schemas/regions/',
#         'stDim':           libxmp.consts.XMP_NS_XMP_Dimensions,
#         'stArea':          'http://ns.adobe.com/xmp/sType/Area#',
#         'stDim':           'http://ns.adobe.com/xap/1.0/sType/Dimensions#',
#         'photoshop':       libxmp.consts.XMP_NS_Photoshop,
#         'apple-fi':        "http://ns.apple.com/faceinfo/1.0/",
#         'Iptc4xmpExt':     'http://iptc.org/std/Iptc4xmpExt/2008-02-29/',
#         'Iptc4xmpCore':    'http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/',
#         'xmpMM':           libxmp.consts.XMP_NS_XMP_MM,
#         'xmpDM':           libxmp.consts.XMP_NS_DM,
#         'xmpRights':       libxmp.consts.XMP_NS_XMP_Rights,
#         'MicrosoftPhoto':  'http://ns.microsoft.com/photo/1.0/',
#         'PhotoCuration':   'http://avi.alkalay.net/PhotoCuration/xmlns/1.0'
#     }
#
#     tagMap=[
#         ('dc', 'creator', 'author', 'list'),
#         ('dc', 'description', 'suggested_caption'),
#         ('dc', 'source', 'uuid'),
#         ('dc', 'subject', 'keywords'),
#         ('dc', 'title', 'suggested_caption'),
#         ('xmp', 'CreatorTool', 'app_creator'),
#         ('xmp', 'Nickname', '{filename}'),
#         ('xmp', 'Rating', '{favorited_percent}'),
#         ('xmpRights', 'Owner', 'device_owner', 'list'),
#
#         ('xmpMM', 'DocumentID', 'uuid'),
#
#         ('xmpDM', 'shotLocation', 'location_suggested_name'),
#         ('photoshop', 'Country', 'location_country'),
#         ('photoshop', 'State', 'location_state'),
#         ('photoshop', 'City', 'location_city'),
#
#
#         ('dc', 'identifier', 'uuid'),
#
#         ('xmpDM', 'album', '{albums_list}'),
#         ('xmpDM', 'artist', 'author'),
#
#         ('xmpDM', 'scene', 'location_context'),
#         ('Iptc4xmpExt', 'PersonInImage', 'people_list'),
#
#
#         ('Iptc4xmpExt', 'City', 'location_city'),
#         ('Iptc4xmpExt', 'CountryCode', 'location_countryCode'),
#         ('Iptc4xmpExt', 'CountryName', 'location_country'),
#         ('Iptc4xmpExt', 'ProvinceState', 'location_state'),
#         ('Iptc4xmpExt', 'Sublocation', 'location_subLocality'),
#         ('Iptc4xmpExt', 'WorldRegion', 'location_context'),
#
#         ('MicrosoftPhoto', 'CameraSerialNumber', 'device_serial_number'),
#         ('MicrosoftPhoto', 'LensManufacturer', 'camera_lens_make', 'nooverwrite'),
#         ('MicrosoftPhoto', 'LensModel', 'camera_lens_model', 'nooverwrite'),
#         ('MicrosoftPhoto', 'Rating', '{favorited_5stars}'),
#         ('MicrosoftPhoto', 'LastKeywordXMP', 'keywords'),
#     ]
#
#
#     facesTamplate=jinja2.Template('''
#         <?xpacket begin="<feff>" id="W5M0MpCehiHzreSzNTczkc9d"?>
#         <x:xmpmeta xmlns:x="adobe:ns:meta/">
#         <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
#
#          <rdf:Description rdf:about=""
#           xmlns:apple-fi="http://ns.apple.com/faceinfo/1.0/"
#           xmlns:PhotoCuration="http://avi.alkalay.net/PhotoCuration/xmlns/1.0"
#           xmlns:mwg-rs="http://www.metadataworkinggroup.com/schemas/regions/"
#           xmlns:stArea="http://ns.adobe.com/xmp/sType/Area#"
#           xmlns:stDim="http://ns.adobe.com/xap/1.0/sType/Dimensions#">
#           <mwg-rs:Regions rdf:parseType="Resource">
#            <mwg-rs:AppliedToDimensions rdf:parseType="Resource">
#             <stDim:unit>pixel</stDim:unit>
#             <stDim:w>4032</stDim:w>
#             <stDim:h>3024</stDim:h>
#            </mwg-rs:AppliedToDimensions>
#            <mwg-rs:RegionList>
#             <rdf:Bag>
#             {% for f in people -%}
#              <rdf:li rdf:parseType="Resource">
#                   <mwg-rs:Type>{{f.Type}}</mwg-rs:Type>
#                   <mwg-rs:Name>{{f.Name}}</mwg-rs:Type>
#                   <mwg-rs:Area rdf:parseType="Resource">
#                        <stArea:unit>normalized</stArea:unit>
#                        <stArea:x>{{f.Area.x}}</stArea:x>
#                        <stArea:y>{{f.Area.y}}</stArea:y>
#                        <stArea:w>{{f.Area.w}}</stArea:w>
#                        <stArea:h>{{f.Area.h}}</stArea:h>
#                   </mwg-rs:Area>
#                   <mwg-rs:Extensions rdf:parseType="Resource">
#                        <PhotoCuration:ShortName>{{f.ShortName}}</PhotoCuration:ShortName>
#                        <PhotoCuration:FaceUUID>{{f.person_uuid}}</PhotoCuration:FaceUUID>
#                        <PhotoCuration:FaceURI>{{f.person_uri}}</PhotoCuration:FaceURI>
#                        <apple-fi:FaceID>{{f.person_id}}</apple-fi:FaceID>
#
#                        <PhotoCuration:FaceSize>{{f.Area.facesize_normal}}</PhotoCuration:FaceSize>
#
#                        <PhotoCuration:CenterPixX>{{f.Area.center_xpix}}</PhotoCuration:CenterPixX>
#                        <PhotoCuration:CenterPixY>{{f.Area.center_ypix}}</PhotoCuration:CenterPixY>
#
#                        <PhotoCuration:RightEyePixX>{{f.Area.righteye_xpix}}</PhotoCuration:RightEyePixX>
#                        <PhotoCuration:RightEyePixY>{{f.Area.righteye_ypix}}</PhotoCuration:RightEyePixY>
#
#                        <PhotoCuration:LeftEyePixX>{{f.Area.lefteye_xpix}}</PhotoCuration:LeftEyePixX>
#                        <PhotoCuration:LeftEyePixY>{{f.Area.lefteye_ypix}}</PhotoCuration:LeftEyePixY>
#
#                        <PhotoCuration:MouthPixX>{{f.Area.mouth_xpix}}</PhotoCuration:MouthPixX>
#                        <PhotoCuration:MouthPixY>{{f.Area.mouth_ypix}}</PhotoCuration:MouthPixY>
#                   </mwg-rs:Extensions>
#              </rdf:li>
#             {% endfor -%}
#              <rdf:li rdf:parseType="Resource">
#               <mwg-rs:Type>Focus</mwg-rs:Type>
#               <mwg-rs:Area rdf:parseType="Resource">
#                <stArea:unit>normalized</stArea:unit>
#                <stArea:h>0.46500000000000002</stArea:h>
#                <stArea:w>0.42799999999999999</stArea:w>
#                <stArea:x>0.50900000000000001</stArea:x>
#                <stArea:y>0.41749999999999998</stArea:y>
#               </mwg-rs:Area>
#              </rdf:li>
#             </rdf:Bag>
#            </mwg-rs:RegionList>
#           </mwg-rs:Regions>
#          </rdf:Description>
#         </rdf:RDF>
#         </x:xmpmeta>
#         <?xpacket end='w'?>
#     ''')
#
#
#
#
#     def __init__(self):
#         self.logger=logging.getLogger('{a}.{b}'.format(a=__name__, b=type(self).__name__))
#
#         for n in self.xmpNamespaces:
#             libxmp.XMPMeta.register_namespace(suggested_prefix=n, namespace_uri=self.xmpNamespaces[n])
#
#
#     def getXMP(self,file):
#         xmpfile=libxmp.XMPFiles(file_path=file, open_forupdate=False)
#         xmp=xmpfile.get_xmp()
#         xmpfile.close_file()
#
#         return xmp
#
#
#
#     def addFaces(self, incarnation):
#         """
#         Instrument asset's XMP (masterDoc) adding regions with face names to it.
#         """
#
#         if incarnation['people']:
#             masterDoc = bs4.BeautifulSoup(incarnation['xmp'].serialize_to_str(), "xml")
#
#             regionsDoc = bs4.BeautifulSoup(self.facesTamplate.render({'people': incarnation['people']}), "xml")
#
#             if masterDoc:
#                 # Register all namespaces
#                 root=masterDoc.find('rdf:Description')
#                 for n in self.xmpNamespaces:
#                     root['xmlns:' + n] = self.xmpNamespaces[n]
#
#
#
#                 # Check if there are any 'Regions'?
#                 r=masterDoc.find('mwg-rs:Regions')
#
#                 if r:
#                     # Find original 'Focus' region and save it
#                     focus=r.find('rdf:li').find('mwg-rs:Type').find(text='Focus')
#                     if focus:
#                         focus=focus.parent().parent() # get to the `rdf:li` element
#
#                         # Detach the Focus struct information
#                         focus.extract()
#                         # Transplant it to the new Regions struct
#                         regionsDoc.find('mwg-rs:Regions').find('mwg-rs:RegionList').find('rdf:Bag').append(focus)
#
#                     # Delete former `Regions`
#                     r.decompose()
#
#                 # Append the named regions into the `<rdf:Description>` tag
#                 masterDoc.find('rdf:Description').append(regionsDoc.find('mwg-rs:Regions'))
#             else:
#                 # No initial XMP to instrument, so make the whole generated Regions XMP the definitive
#                 masterDoc=regionsDoc
#
#             self.logger.debug(masterDoc.prettify())
#
#             incarnation['xmp']=libxmp.core.XMPMeta(xmp_str=str(masterDoc))
#
#
#
#
#     def tag(self,incarnation):
#         for m in self.tagMap:
#             modifier=None
#             (nsPrefix,xmpTagName,photoCurationTagName) = (m[0],m[1],m[2])
#             if len(m)==4:
#                 modifier=m[3]
#
#             self.logger.debug(photoCurationTagName)
#
#             value=None
#             if '{' in photoCurationTagName:
#                 # Use format()
#                 value=photoCurationTagName.format(**incarnation['tags'])
#             elif photoCurationTagName in incarnation['tags']:
#                 value=incarnation['tags'][photoCurationTagName]
#
#             try:
#                 if modifier and 'nooverwrite' in modifier and incarnation['xmp'].does_property_exist(self.xmpNamespaces[nsPrefix], xmpTagName):
#                     # Do not touch this existing XMP tag
#                     pass
#                 else:
#                     if value:
#                         if modifier and 'list' in modifier:
#                             value=[value]
#
#                         if isinstance(value, list):
#                             for i in range(len(value)):
#                                 incarnation['xmp'].append_array_item(
#                                         self.xmpNamespaces[nsPrefix],
#                                         xmpTagName,
#                                         value[i],
#                                         {
#                                             'prop_array_is_ordered': False,
#                                             'prop_value_is_array': True
#                                         }
#                                 )
#                         else:
#                             incarnation['xmp'].set_property(
#                                 self.xmpNamespaces[nsPrefix],
#                                 xmpTagName,
#                                 value
#                             )
#             except Exception as e:
#                 logging.error("«{}:{}»: «{}» ({})".format(nsPrefix,xmpTagName,value,type(value)))
#                 raise e
#
#
#         self.addFaces(incarnation)
#
#         xmpfile=libxmp.XMPFiles(file_path=str(incarnation['tags']['filename']), open_forupdate=True)
#         if xmpfile.can_put_xmp(incarnation['xmp']):
#             # Embed XMP in supported formats
#             xmpfile.put_xmp(incarnation['xmp'])
#             xmpfile.close_file()
#         else:
#             # Write tags to sidecar XMP file when handling unsupported formats (HEIC?)
#             xmpfile.close_file()
#             xmpfile=libxmp.XMPFiles(file_path=str(incarnation['tags']['filename'])+".xmp", open_forupdate=True)
#             xmpfile.put_xmp(incarnation['xmp'])
#             xmpfile.close_file()
#
# #         if incarnation['people']:
# #             t='Xmp.dwc.Record/dcterms:bibliographicCitation'
# #             tag=pyexiv2.XmpTag(t,json.dumps(incarnation['people'],indent=4,ensure_ascii=False))
# #             incarnation['meta'][t]=tag
#
#



class WallclockSubtitles:
    # HANDLING OF TIME ACROSS VARIOS VIDEO TYPES
    #
    # * normal video
    #     * video_duration == recording_duration
    #     * subtitles update frequency: 1s
    #     * delta between wall clock ticks: 1s
    #     * subtitle text precision: 1s
    #     * number of subtitles: int(video_duration)
    # * time lapse
    #     * video_duration ≪ recording_duration
    #     * subtitles update frequency: 0.2s (5 per second)
    #     * delta between wall clock ticks: (recordingDuration×freqUpdate÷precision)÷videoDuration
    #     * subtitle text precision: 1s
    #     * number of subtitles: recordingDuration×freqUpdate÷precision
    # * slow motion
    #     * video_duration ≫ recording_duration
    #     * subtitles update frequency: 0.2s (5 per second)
    #     * delta between wall clock ticks: 0.2s
    #     * subtitle text precision: 0.1s (time is 01:02:03.4)
    #     * number of subtitles: recordingDuration×freqUpdate÷precision

    subtitleSRTitemTemplate='{index}\n'\
        '{start} --> {end}\n'\
        '{text}\n'

    def __init__(
                self,
                startTime,
                recordingDuration,
                videoDuration,
                circa=False,
                samplesPerVideoSecond=1,
                wallclockFormat='%a %Y-%m-%d %H:%M:%S %z'
        ):

        # Format for time on SRT files
        self.timecodeFormat='%H:%M:%S,%f' #srt

        # Default time format to be displayed as subtitles
        self.wallclockFormat=wallclockFormat


        self.startTime=startTime
        self.circa=circa
        self.recordingDuration=recordingDuration
        self.videoDuration=videoDuration

        if self.videoDuration < 1:
            # Video too short for subtitles, so augment it
            augmentationScale=1.5/self.videoDuration
            self.videoDuration*=augmentationScale
            self.recordingDuration*=augmentationScale

        # how many seconds of story fit in a second of video
        self.storyTimePerVideoTime=recordingDuration/videoDuration

        # story time between 2 subtitle samples (>1 in time lapses, <1 in slow motion)
        self.deltaOnStoryTime=1

        # how many different subtitles I want in 1 second of video
        self.samplesPerVideoSecond=samplesPerVideoSecond

        if self.recordingDuration != self.videoDuration:
            # Time lapse or slow motion
            self.samplesPerVideoSecond=5

        if self.recordingDuration < self.videoDuration:
            # Slow motion
            self.wallclockFormat='%a %Y-%m-%d %H:%M:%S.%f %z'

        # time step between each wall clock tick
        self.deltaOnStoryTime = self.storyTimePerVideoTime / self.samplesPerVideoSecond

        # number of subtitle samples to generate
        self.samples = int(math.floor(self.recordingDuration / self.deltaOnStoryTime))

        self.logger=logging.getLogger('{a}.{b}'.format(a=__name__, b=type(self).__name__))



    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pprint.pformat(vars(self), indent=4, width=1)



    def generate(self):
        # Generate the wall clock that will be presented as subtitles
        self.wallclock=pd.date_range(
            start=self.startTime,
            end=(
                self.startTime +
                datetime.timedelta(seconds=(self.samples * self.deltaOnStoryTime))
            ),
            periods=self.samples
        )

        # Generate the timecodes for each subtitle
        self.timecodes=pd.date_range(
            start=datetime.datetime(2000,1,1),
            end=(
                datetime.datetime(2000,1,1)+
                datetime.timedelta(seconds=(self.samples * self.deltaOnStoryTime / self.storyTimePerVideoTime))
            ),
            periods=self.samples + 1
        )

        # Assemble together all data framework for wall clock subtitles
        self.subtitles=pd.DataFrame({
            'start': self.timecodes[:-1], # all but last timecode
            'end':   self.timecodes[1:], # all but first timecode
            'text':  self.wallclock
        })

        return self



    def dumpSRT(self, fileName):
        # Write subtitles to a file
        # currentIncarnation['decryptedFileInfo']['decryptedFilePath']+'.srt'
        with open(fileName,'w') as subs:
            for i,s in self.subtitles.iterrows():
                print(self.subtitleSRTitemTemplate.format(
                        index=i+1,
                        start=s['start'].strftime(self.timecodeFormat)[:12],
                        end=s['end'].strftime(self.timecodeFormat)[:12],
                        text=s['text'].strftime(self.wallclockFormat)+self.circa*' (circa)'
                    ),
                    file=subs
                )


    def dumpWEBVTT(self, fileName):
        # Write subtitles to a file
        # currentIncarnation['decryptedFileInfo']['decryptedFilePath']+'.srt'
        with open(fileName,'w') as subs:
            print('WEBVTT\n',file=subs)
            for i,s in self.subtitles.iterrows():
                print("{} --> {}\n{}\n".format(
                        s['start'].strftime(self.timecodeFormat),
                        s['end'].strftime(self.timecodeFormat),
                        s['text'].strftime(self.wallclockFormat)+self.circa*' (circa)'
                    ),
                    file=subs
                )

