import sys
# sys.path.insert(0,"..") # Adds higher directory to python modules path.

#### TODO
# - Write photo XMP tags
# - Handle no model tag and fill with other attributes




from iOSbackup import iOSbackup
import sqlite3
import configparser
import sys
import os
import io
import biplist
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
import ffmpeg
import dateutil
import datetime
import math
import tempfile
import exifread
import mutagen
import re
import json
import subprocess




try:
    # A powerfull module that can write XMP tags, but available only on Linux
    import pyexiv2

    # To install this module in Fedora:
    # (first, as root) dnf install gcc-c++ boost-python3 exiv2-devel python3-devel
    # (then, as regular user) pip3 install -U py3exiv2 --user
except (ImportError, RuntimeError):
    # Module not installed on system (ImportError) or installed but useless on macOS (RuntimeError)
    pass



# logging.basicConfig(level=logging.DEBUG)
module_logger = logging.getLogger(__name__)



filenaneTemplate="""{#- -#}
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
.{{original_file_extension -}}
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
    """

    assetTypes={ # match with `kind_encoded` from `listOfAssets` query
        '0>0':     'image', # JPG, HEIC, PNG, GIF
        '0>0>2':   'animated GIF',
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
                ZADDITIONALASSETATTRIBUTES.ZREVERSELOCATIONDATA as location_data,
                ZADDITIONALASSETATTRIBUTES.ZCREATORBUNDLEID as app_creator,
                ZADDITIONALASSETATTRIBUTES.ZEDITORBUNDLEID as app_editor,
                coalesce(ZADDITIONALASSETATTRIBUTES.ZCREATORBUNDLEID,ZADDITIONALASSETATTRIBUTES.ZEDITORBUNDLEID) as app_creator_or_editor,
                facecount.facecount,
                named_facecount.named_facecount
            from
                ZASSET

                left outer join ZADDITIONALASSETATTRIBUTES
                    on ZADDITIONALASSETATTRIBUTES.ZASSET=ZASSET.Z_PK

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
                ZMEMORY.ZUSERCREATED as memory_usercreated,
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
            select
                ZASSET.Z_PK as Asset_PK,
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

                people.LEFTEYE_normalizedx,
                people.LEFTEYE_normalizedy,
                people.RIGHTEYE_normalizedx,
                people.RIGHTEYE_normalizedy,
                people.MOUTH_normalizedx,
                people.MOUTH_normalizedy,
                people.CENTER_normalizedx,
                people.CENTER_normalizedy,

                people.face_size,
                people.person_uri,
                people.person_uuid
            from
            	ZASSET,
                (
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

                        ZDETECTEDFACE.ZLEFTEYEX as LEFTEYE_normalizedx,
                        ZDETECTEDFACE.ZLEFTEYEY as LEFTEYE_normalizedy,
                        ZDETECTEDFACE.ZRIGHTEYEX as RIGHTEYE_normalizedx,
                        ZDETECTEDFACE.ZRIGHTEYEY as RIGHTEYE_normalizedy,
                        ZDETECTEDFACE.ZMOUTHX as MOUTH_normalizedx,
                        ZDETECTEDFACE.ZMOUTHY as MOUTH_normalizedy,
                        ZDETECTEDFACE.ZCENTERX as CENTER_normalizedx,
                        ZDETECTEDFACE.ZCENTERY as CENTER_normalizedy,

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
            where people.asset=ZASSET.Z_PK;
    """

    domain='CameraRollDomain'

    original='Media/{dcim_folder}/{file}'
    mutation='Media/PhotoData/Mutations/{dcim_folder}/{file_no_extension}/Adjustments/FullSizeRender.{file_extension}'

    referenceFPS=30 # Convert slowmotion (240fps) to this reference FPS

    def __init__(self,
                configFile=None,
                author=None, # author of photos
                device_owner=None,
                start=None,
                end=None,
                extractTypes=None,
                target=None, # folder to receive files
                originals=['1>101', '0>2>3>0', '0>2>3>3', '0>2>5>1', '0>2>5>2'], # either to extract also originals or not
                trashed=False,
                filenameTemplate=filenaneTemplate
        ):

        self.logger=logging.getLogger('{a}.{b}'.format(a=__name__, b=type(self).__name__))

        if start:
            self.start=pd.Timestamp(start).to_pydatetime()
        else:
            self.start=start

        if end:
           self.end=pd.Timestamp(end).to_pydatetime()
        else:
            self.end=end

        self.author=author
        self.device_owner=device_owner
        self.target=target
        self.trashed=trashed
        self.extractTypes=extractTypes

        # Handling of originals
        self.originals=originals

        j2=jinja2.Environment()
        j2.filters['secure']=PhotoCuration.secureFileName
        self.filenameTemplate=j2.from_string(filenameTemplate)

        self.iosDBs={}
        self.loadConfig(configFile)
        logging.debug(dict(self.config))

        backuproot=None
        if 'global' in self.config and 'backup' in self.config['global']:
            backuproot=self.config['global']['backup']

        self.ios=iOSbackup(udid=self.config['device']['UDID'], derivedkey=self.config['device']['decryptionkey'], backuproot=backuproot)
        self.getiOSfiles()
        self.getPhotoDB()




    def __del__(self):
        self.db.close()
        del self.ios
        for f in self.iosDBs:
            os.remove(self.iosDBs[f]['decryptedFilePath'])


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


    def extractAndTag(self):
        if self.target:
            Path(self.target).mkdir(parents=True, exist_ok=True)

        # At this point, this is the columns we have on self.assets:
        # Index(['dcim_folder', 'file', 'caption', 'trashed', 'kind', 'favorited',
        #        'width', 'height', 'video_duration', 'uuid', 'moment_title',
        #        'moment_subtitle', 'creation_timestamp', 'utc_time', 'tz_offset',
        #        'asset_local_time', 'exif_timestamp', 'facecount', 'named_facecount',
        #        'location_name', 'location_context', 'location_street',
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
            'asset_local_time',
            'infered_asset_caption',
            'kind_encoded',
            'kind_description',
            'favorited',
            'width',
            'height',
            'video_duration',
            'uuid',
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
            'tz_offset',
            'infered_asset_caption_score',
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

        self.tags['author']=self.author

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
                        'tags': assetCurrent[1],
                    }
                }
            }

            self.logger.warning("Working on {}".format(assetCurrent['incarnations']['master']['tags']['original_file']))

            # Merge timezone offset into creation_local_object
            assetCurrent['incarnations']['master']['tags']['creation_local_object']=(
                assetCurrent['incarnations']['master']['tags']['creation_local_object']
                .tz_localize(assetCurrent['incarnations']['master']['tags']['tz_offset'])
            )

            # Get people and faces of asset
            assetCurrent['incarnations']['master']['people']=self.getAssetPeople(assetCurrent['pk'])

            # initialize file name collision handling artifacts
            assetCurrent['incarnations']['master']['tags']['collision_index'] = 0
            assetCurrent['incarnations']['master']['tags']['original_file_no_extension']=os.path.splitext(assetCurrent['incarnations']['master']['tags']['original_file'])[0]
            assetCurrent['incarnations']['master']['tags']['original_file_extension']=os.path.splitext(assetCurrent['incarnations']['master']['tags']['original_file'])[1][1:].strip().lower()

            self.assetCurrent=assetCurrent

            if assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>0') or assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>10'): # and 'gif' not in assetCurrent['incarnations']['master']['tags']['original_file_extension']:
                # Regular image as JPG, HEIC, PNG, GIF, DNG
                self.handleImage(assetCurrent)

#             if assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>10'):
#                 # Regular image as JPG, HEIC, PNG, GIF, DNG
#                 self.handleImage(assetCurrent)

            if assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('1>'):
                # Various types of video
                self.handleVideo(assetCurrent)

            if assetCurrent['incarnations']['master']['tags']['kind_encoded'].startswith('0>2'):
                # Handle Live photos, the image part
                self.handleImage(assetCurrent)

#                 if assetCurrent['incarnations']['master']['tags']['kind_encoded'] != '0>2>3>3':
                # Now morph it into a video to handle the video part
                self.logger.debug(f"Handling video part of Live Photo {assetCurrent['incarnations']['master']['tags']['original_file']}")

                # Delete image incarnations to start fresh
                deletes=set(assetCurrent['incarnations'].keys())
                deletes.remove('master')
                for i in deletes:
                    del assetCurrent['incarnations'][i]

                assetCurrent['incarnations']['master']['tags']['original_file']=assetCurrent['incarnations']['master']['tags']['original_file_no_extension']+'.MOV'
                assetCurrent['incarnations']['master']['tags']['original_file_extension']='mov'
                self.handleVideo(assetCurrent)






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

        regions=[]
        for i,f in self.peopleOfAssets.query(f'Asset_PK=={assetPK}').iterrows():
            region={}
            region['Type']='Face'
            for k in faceKeyMap:
                if '/' in k:
                    parts=k.split('/')
                    if parts[0] not in region:
                        region[parts[0]]={}
                    region[parts[0]][parts[1]]=f[faceKeyMap[k]]
                else:
                    region[k]=f[faceKeyMap[k]]

            # face_size in pixels = face_size × √(width²+height²)
            region['Area']['facesize_pix']=f['face_size']
            region['Area']['facesize_pix']*=math.sqrt(f['width']*f['width'] + f['height']*f['height'])
            region['Area']['x']=region['Area']['center_xpix']-region['Area']['facesize_pix']/2
            region['Area']['y']=region['Area']['center_ypix']-region['Area']['facesize_pix']/2
            region['Area']['w']=region['Area']['facesize_pix']
            region['Area']['h']=region['Area']['facesize_pix']

            regions.append(region)

        if len(regions)>0:
            return regions
        else:
            return None





    def handleVideo(self, asset):
        # Get original video timecodes

        currentIncarnation=asset['incarnations']['master']


        #mark BEGIN read original video and metadata

        currentIncarnation['backupfile']=self.original.format(
            dcim_folder=currentIncarnation['tags']['dcim_folder'],
            file=currentIncarnation['tags']['original_file']
        )

        # Extract image from iOS backup and put it into target folder with a temporary name
        currentIncarnation['decryptedFileInfo']=self.ios.getFileDecryptedCopy(
            relativePath=currentIncarnation['backupfile'],
            targetFolder=self.target
        )

        self.logger.debug(f"ffprobe {currentIncarnation['decryptedFileInfo']['decryptedFilePath']}")
        currentIncarnation['meta']=ffmpeg.probe(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])

        metaToTags=[
            # exifread bindings
            ('media_create_time', 'creation_time'),
            ('camera_make', 'com.apple.quicktime.make'), # Apple
            ('camera_model', 'com.apple.quicktime.model'), # iPhone 11 Pro
            ('camera_software_version', 'com.apple.quicktime.software') # 14.2
        ]

        # Get video number of frames per second; useful to handle slow motion videos
        try:
            # Try to find video on first track
            currentIncarnation['tags']['framerate']=currentIncarnation['meta']['streams'][0]['avg_frame_rate']
            currentIncarnation['tags']['framerate']=currentIncarnation['tags']['framerate'].split('/')
            currentIncarnation['tags']['framerate']=int(currentIncarnation['tags']['framerate'][0])/int(currentIncarnation['tags']['framerate'][1])
        except ZeroDivisionError:
            # Try to find video on second track
            currentIncarnation['tags']['framerate']=currentIncarnation['meta']['streams'][1]['avg_frame_rate']
            currentIncarnation['tags']['framerate']=currentIncarnation['tags']['framerate'].split('/')
            currentIncarnation['tags']['framerate']=int(currentIncarnation['tags']['framerate'][0])/int(currentIncarnation['tags']['framerate'][1])


        # Update the tags dict with video tags extracted from file
        for varname,tagname in metaToTags:
            try:
                currentIncarnation['tags'][varname]=currentIncarnation['meta']['format']['tags'][tagname]
            except KeyError:
                # desired tag unavailable in video, so ignore it.
                pass

        # Get video file create time; useful to calculate wall clock duration of unclipped time lapse videos
        currentIncarnation['tags']['media_create_time']=dateutil.parser.parse(currentIncarnation['tags']['media_create_time'])

        # Get video duration
        currentIncarnation['tags']['video_duration']=float(currentIncarnation['meta']['format']['duration'])

        #mark END read original video and metadata


        #mark BEGIN basic decisions about slowmotion, timelapse etc

        if '1>102' in currentIncarnation['tags']['kind_encoded']:
            # Timelapse videos recording time is the time media was created minus the time the recording was started
            currentIncarnation['tags']['variation']='timelapse'
            currentIncarnation['tags']['recording_duration']=(
                currentIncarnation['tags']['media_create_time'].astimezone(None)-
                currentIncarnation['tags']['creation_utc_object'].to_pydatetime()
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

            # video duration on wannabe slow motion videos is fps/newfps time longer
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

            self.logger.debug(f"ffprobe {currentIncarnation['decryptedFileInfo']['decryptedFilePath']}")
            currentIncarnation['meta']=ffmpeg.probe(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])

            metaToTags=[
                # exifread bindings
                ('camera_make', 'com.apple.quicktime.make'), # Apple
                ('camera_model', 'com.apple.quicktime.model'), # iPhone 11 Pro
                ('camera_software_version', 'com.apple.quicktime.software'), # 14.2
                ('tag_creation_date','com.apple.quicktime.creationdate'), #=2020-11-07T16:42:21-0300
                ('location_accuracy_horizontal', 'com.apple.quicktime.location.accuracy.horizontal'), #=65.000000
                ('location_ISO6709', 'com.apple.quicktime.location.ISO6709') #=-23.5506-046.6835+792.764/
            ]

            # Update the tags dict with video tags extracted from file
            for varname,tagname in metaToTags:
                try:
                    currentIncarnation['tags'][varname]=currentIncarnation['meta']['format']['tags'][tagname]
                except KeyError:
                    # information for 'tagname' unavailable in video, so ignore it.
                    pass

            # Get video number of frames per second; useful to handle slow motion videos
            try:
                # Try to find video on first track
                currentIncarnation['tags']['framerate']=currentIncarnation['meta']['streams'][0]['avg_frame_rate']
                currentIncarnation['tags']['framerate']=currentIncarnation['tags']['framerate'].split('/')
                currentIncarnation['tags']['framerate']=int(currentIncarnation['tags']['framerate'][0])/int(currentIncarnation['tags']['framerate'][1])
            except ZeroDivisionError:
                # Try to find video on second track
                currentIncarnation['tags']['framerate']=currentIncarnation['meta']['streams'][1]['avg_frame_rate']
                currentIncarnation['tags']['framerate']=currentIncarnation['tags']['framerate'].split('/')
                currentIncarnation['tags']['framerate']=int(currentIncarnation['tags']['framerate'][0])/int(currentIncarnation['tags']['framerate'][1])

            # Get video duration
            currentIncarnation['tags']['video_duration']=float(currentIncarnation['meta']['format']['duration'])

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
            try:
                currentIncarnation['tags']['video_rotation']=int(currentIncarnation['meta']['streams'][0]['tags']['rotate'])
            except KeyError:
                # OK, no orientation information
                pass

            # Find video codec
            currentIncarnation['tags']['video_codec']=currentIncarnation['meta']['streams'][0]['codec_name']

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




            #mark BEGIN Write tags and metadata to a file
            currentIncarnation['tmp']['metadata']=tempfile.NamedTemporaryFile(suffix='.ffmetadata',dir=self.target, delete=False)
            currentIncarnation['tmp']['metadata'].close()
            currentIncarnation['tmp']['metadata']=currentIncarnation['tmp']['metadata'].name
            with open(currentIncarnation['tmp']['metadata'],'w') as metadata:
                print(';FFMETADATA1',file=metadata)

                for tagname in currentIncarnation['meta']['format']['tags']:
                    print(
                        "{}={}".format(
                            tagname,
                            currentIncarnation['meta']['format']['tags'][tagname]
                        ),
                        file=metadata
                    )

                tagMap=[
                    ('Xmp.dc.source', '{dcim_folder}/{original_file}'),
                    ('Xmp.xmpMM.DocumentID', 'uuid'),
                    ('Xmp.iptcExt.PersonInImage', 'people_list'),
                    ('Xmp.xmp.Rating', 'favorited_percent'),

                    ('Xmp.xmpDM.scene', 'location_context'),
                    ('Xmp.iptcExt.City', 'location_city'),
                    ('Xmp.iptcExt.CountryCode', 'location_countryCode'),
                    ('Xmp.iptcExt.CountryName', 'location_country'),
                    ('Xmp.iptcExt.ProvinceState', 'location_state'),
                    ('Xmp.iptcExt.Sublocation', 'location_subLocality'),
                    ('Xmp.iptcExt.WorldRegion', 'location_context'),
                ]

                for m in tagMap:
                    fileTagName,photoCurationTagName=m[0],m[1]
                    if len(m)==3:
                        modifier=m[2]
                    else:
                        modifier=None

                    value=None
                    if '{' in photoCurationTagName:
                        # Use format()
                        value=photoCurationTagName.format(**currentIncarnation['tags'])
                    elif photoCurationTagName in currentIncarnation['tags']:
                        value=currentIncarnation['tags'][photoCurationTagName]

                    if modifier and 'nooverwrite' in modifier and fileTagName in incarnation['meta']:
                        # Do not touch this existing exif/xmp/iptc tag
                        pass
                    else:
                        if value:
                            self.logger.debug('{}: ({}){}'.format(fileTagName,type(value),value))
                            if modifier and 'list' in modifier:
                                value=[value]

                            print("{}={}".format(fileTagName,value),file=metadata)

            #mark END Write tags and metadata to a file


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
                metadata  = ffmpeg.input(currentIncarnation['tmp']['metadata'])


                ffmpegFlags={
                    'metadata:s:s:0': 'title=Wall clock',
                    'tag:s:s:0': 'tx3g'

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



                    muxer=ffmpeg.output(
                            metadata,
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
                            metadata,
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

                try:
                    self.logger.debug('"' + '" "'.join(muxer.compile()) + '"')
                    PhotoCuration.myMuxerRun(muxer)
#                     muxer.run()
                except Exception as e:
                    self.logger.error(currentIncarnation['subs'])
                    raise e

                del subtitles

                #mark BEGIN old fashion tagging
#                 currentIncarnation['meta']=mutagen.File(str(currentIncarnation['tags']['filename']))
#                 self.tagVideo(currentIncarnation)
                #mark END old fashion tagging

        #mark END iterate over all incarnations

        #mark BEGIN cleanup

        for incarnation in asset['incarnations']:
            currentIncarnation=asset['incarnations'][incarnation]

            try:
                os.remove(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])
            except (FileNotFoundError,KeyError):
                # File wasa not tracked or was deleted by a previous incarnation cleanup
                pass

            if 'tmp' in currentIncarnation:
                self.logger.debug("Cleanup: " + str(currentIncarnation['tmp']))
                for i in currentIncarnation['tmp']:
                    os.remove(currentIncarnation['tmp'][i])



        #mark END cleanup



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

        #mark BEGIN decisions about originals
        if asset['incarnations']['master']['tags']['edited']:
            # Extract mutation and get file tags


#               original='Media/{dcim_folder}/{file}'
#               mutation='Media/PhotoData/Mutations/{dcim_folder}/{file_no_extension}/Adjustments/FullSizeRender.{file_extension}'

            if (type(self.originals) is bool and self.originals) or (type(self.originals) is list and asset['incarnations']['master']['tags']['kind_encoded'] in self.originals):
                # Calculate original file name
                asset['incarnations']['original']={}
                asset['incarnations']['original']['tags']=copy.deepcopy(asset['incarnations']['master']['tags'])
                asset['incarnations']['original']['people']=copy.deepcopy(asset['incarnations']['master']['people'])
                asset['incarnations']['original']['tags']['unedited']=True

                asset['incarnations']['original']['backupfile']=self.original.format(
                    dcim_folder=asset['incarnations']['original']['tags']['dcim_folder'],
                    file=asset['incarnations']['original']['tags']['original_file']
                )

            if 'png' in asset['incarnations']['master']['tags']['original_file_extension']:
                # Edited PNGs become JPGs
                asset['incarnations']['master']['tags']['original_file_extension']='jpg'

            asset['incarnations']['master']['backupfile']=self.mutation.format(
                dcim_folder=asset['incarnations']['master']['tags']['dcim_folder'],
                file_no_extension=asset['incarnations']['master']['tags']['original_file_no_extension'],
                file_extension=asset['incarnations']['master']['tags']['original_file_extension'],
            )
        else:
            # The 'master' spawn is the original file
            asset['incarnations']['master']['backupfile']=self.original.format(
                dcim_folder=asset['incarnations']['master']['tags']['dcim_folder'],
                file=asset['incarnations']['master']['tags']['original_file']
            )

        #mark END decisions about originals

        # At this point we have all incarnations that we desire, mostly 'main' and 'original'


        #mark BEGIN itarate over incarnations
        for incarnation in asset['incarnations']:
            currentIncarnation=asset['incarnations'][incarnation]



            # Extract image from iOS backup and put it into target folder with a temporary name
            currentIncarnation['decryptedFileInfo']=self.ios.getFileDecryptedCopy(
                relativePath=currentIncarnation['backupfile'],
                targetFolder=self.target
            )

            currentIncarnation['tags']['ext'] = os.path.splitext(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])[1][1:].strip().lower()

            #mark BEGIN extract image tags (EXIF, etc)
            metaToTags=[
                # pyexiv2 bindings
                ('camera_make', 'Exif.Image.Make'),
                ('camera_model', 'Exif.Image.Model'),
                ('camera_lens_make', 'Exif.Photo.LensMake'),
                ('camera_lens_model', 'Exif.Photo.LensModel'),
                ('camera_software_version', 'Exif.Image.Software'),

                # exifread bindings
                ('camera_make', 'Image Make'),
                ('camera_model', 'Image Model'),
                ('camera_lens_model', 'EXIF LensModel'),
                ('camera_software_version', 'Image Software')
            ]


            # Try multiple libraries to get file photo tags
            try:
                # Try first with the Py3Exiv2 library. Linux only, write support, no HEIF yet.
    #         if currentIncarnation['tags']['ext'] != 'heic':
                currentIncarnation['meta'] = pyexiv2.ImageMetadata(currentIncarnation['decryptedFileInfo']['decryptedFilePath'])
                currentIncarnation['meta'].read()
            except:
                # Try with Exifread library. All platforms, read only, HEIF support.
                with open(currentIncarnation['decryptedFileInfo']['decryptedFilePath'],'rb') as heif:
                    currentIncarnation['meta']=exifread.process_file(heif)

            #mark END extract image tags (EXIF, etc)


            # Update the tags dict with photo tags extracted from file
            for varname,tagname in metaToTags:
                try:
                    # Try first with the Py3Exiv2 library.
                    currentIncarnation['tags'][varname]=currentIncarnation['meta'][tagname].value
                except AttributeError:
                    # Try with Exifread library (value×values attribute).
                    currentIncarnation['tags'][varname]=currentIncarnation['meta'][tagname].values
                except KeyError:
                    # Exif tag unavailable in image, so ignore it.
                    pass





            # Write EXIF, XMP, IPTC tags
            self.tagImage(currentIncarnation)






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

        #mark END itarate over incarnations






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
            ('%Y.%m.%d-%H.%M.%S', 'time_fs'),
            ('Y', 'year'),
            ('m', 'month'),
            ('d', 'day'),
            ('H', 'hour'),
            ('M', 'minute'),
            ('S', 'second'),
            ('y', 'year_small'),
            ('I', 'hour12'),
            ('p', 'ampm'),
            ('b', 'month_name_abrev'),
            ('B', 'month_name'),
            ('a', 'weekday_abrev'),
            ('A', 'weekday'),
            ('c', 'locale_time')
        ]

        for i in items:
            if '%' in i[0]:
                format=i[0]
            else:
                format=f'%{i[0]}'
            df[f'{prefix}_{i[1]}']=df[col].dt.strftime(format)




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
        self.memories=self.memories.convert_dtypes() # optimize data types

#         datetimeCols=['album_utc_creation','album_utc_start','album_utc_end']

#         for c in datetimeCols:
#             self.albums[c]=pd.to_datetime(self.albums[c], utc=True)

        assets=[]
        for index, memory in self.memories.iterrows():
#             print(memory['ZMOVIEASSETSTATE'][:15])

            if memory['ZMOVIEASSETSTATE'] != b'None':
                try:
                    struct=biplist.readPlistFromString(memory['ZMOVIEASSETSTATE'])
                except biplist.InvalidPlistException:
                    print("{}: Invalid plist".format(memory['memory_title']))
                    continue

                for i in struct['$objects'][struct['$top']['root'].integer]['NS.keys']:
                    assets.append({
                        'memory': index,
                        'memoryUUID': memory['memory_uuid'],
#                         'memoryTrashed': memory['memory_is_trashed'],
                        'assetUUID': struct['$objects'][i.integer]
                    })

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

            struct=biplist.readPlistFromString(data)
            packedAssetUUIDs=struct['$objects'][struct['$top']['assetUUIDs'].integer]

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






    def calcAssetsKeywords(self):
        """
        Add following columns to self.assets:

        albums_list: contains Python list with names of all albums the asset is in.

        memories_list: contains Python list with "title @ subtitle" of all memories the asset is in.

        people_list: contains Python list named of all named people that appear in asset.

        keywords: an emoji-formatted Python list including all the above.
        """

        albumAggregate=[]
        for asset,albums in self.assetsOfAlbums[self.assetsOfAlbums['albumTrashed']==0].join(self.albums, on='album')[['assetUUID','album_title']].groupby('assetUUID'):
            albumsOfAasset={
                'asset_pk': asset,
                'albums_list': list(albums['album_title']),
            }
            albumAggregate.append(albumsOfAasset)

        albumAggregate=pd.DataFrame(albumAggregate).set_index('asset_pk')


        memoryAggregate=[]
        for asset,memories in self.assetsOfMemories.join(self.memories[self.memories['trashed']==0], on='memory')[['assetUUID','memory_title','memory_subtitle']].groupby('assetUUID'):
            memories['memory_title_subtitle']=memories[['memory_title', 'memory_subtitle']].agg(' @ '.join, axis=1)

            memoriesOfAsset={
                'asset': asset,
                'memories_list': list(memories['memory_title_subtitle']),
            }
            memoryAggregate.append(memoriesOfAsset)

        memoryAggregate=pd.DataFrame(memoryAggregate).set_index('asset')


        peopleAggregate=[]
        for asset,people in self.peopleOfAssets.groupby('Asset_PK'):
            peopleOfAAsset={
                'asset': asset,
                'people_list': list(people['full_name']),
            }
            peopleAggregate.append(peopleOfAAsset)

        peopleAggregate=pd.DataFrame(peopleAggregate).set_index('asset')


        # Added to assets: list of albums, list of memories, list of people
        self.assets=self.assets.join(albumAggregate, on='uuid').join(memoryAggregate, on='uuid').join(peopleAggregate)

        def reformat(thelist,element_format):
            if type(thelist) in (list,tuple):
                return [element_format.format(e) for e in thelist]
            else:
                return []


        album_format='🖼{}'
        memory_format='📅{}'
        person_format='🙂{}'

        self.assets['keywords']=self.assets['albums_list'].where(pd.notnull(self.assets['albums_list']),None).apply(reformat,args=[album_format])
        self.assets['keywords']+=self.assets['memories_list'].where(pd.notnull(self.assets['memories_list']),None).apply(reformat,args=[memory_format])
        self.assets['keywords']+=self.assets['people_list'].where(pd.notnull(self.assets['people_list']),None).apply(reformat,args=[person_format])





    def getLocationDataFromPlist(self,plistData):
        try:
            loc=biplist.readPlistFromString(plistData)
        except:
            return None

        location={}

        mapItem_index=loc['$objects'][loc['$top']['root'].integer]['mapItem'].integer
        sortedPlaceInfos_index=loc['$objects'][mapItem_index]['sortedPlaceInfos'].integer

        # Find location_name inside the NSKeyedArchiver object
        if loc['$objects'][loc['$top']['root'].integer]['isHome']:
            location['location_name']='Home'
        else:
            if len(loc['$objects'][sortedPlaceInfos_index]['NS.objects']):
                place_index=loc['$objects'][sortedPlaceInfos_index]['NS.objects'][0].integer
                placeName_index=loc['$objects'][place_index]['name'].integer
                location['location_name']=loc['$objects'][placeName_index]


        # Find location_context inside the NSKeyedArchiver object
        place=[]
        for l in loc['$objects'][sortedPlaceInfos_index]['NS.objects']:
            placeName_index=loc['$objects'][l.integer]['name'].integer
            place.append(loc['$objects'][placeName_index])
        places=set()
        places_add=places.add
        location['location_context']=' ⊂ '.join([x for x in place if not (x in places or places_add(x))])

        mapper={
            # the relationship between my desired keys and the plist keys
            'location_formattedAddress': '_formattedAddress',
            'location_addressString': 'addressString',
            'location_countryCode': '_ISOCountryCode',
            'location_country': '_country',
            'location_postalCode': '_postalCode',
            'location_state': '_state',
            'location_adminArea': '_subAdministrativeArea',
            'location_subLocality': '_subLocality',
            'location_city': '_city',
            'location_street': '_street'
        }

        # Find various items inside the NSKeyedArchiver object
        postalAddress_index=loc['$objects'][loc['$top']['root'].integer]['postalAddress'].integer

        for k in mapper.keys():
            if mapper[k] in loc['$objects'][postalAddress_index]:
                i=loc['$objects'][postalAddress_index][mapper[k]].integer
#                 print("{}: {}".format(type(loc['$objects'][i]),loc['$objects'][i]))
                if loc['$objects'][i] != '$null':
                    location[k]=loc['$objects'][i]

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
        self.assets=self.assets.convert_dtypes()
#
#         if self.start: self.assets=self.assets[self.assets['utc_time']>=self.start]
#         if self.end:   self.assets=self.assets[self.assets['utc_time']<=self.end]
#
#         self.assets=self.assets[self.assets['trashed']==0]

        # Remove a '\n' from Moment title that Apple inserts to look nicer in Moment cards
        self.assets['moment_title']=self.assets['moment_title'].str.replace('\xa0',' ')
        self.assets['utc_time']=self.assets['utc_time'].dt.tz_localize('UTC')
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
            .join(self.albums)[['album_uuid','album_title','album_asset_count','assetUUID']]
            .sort_values('album_asset_count')
            .groupby('assetUUID')
            .head(1)
            .set_index('assetUUID')
        )

        self.assets=self.assets.join(bestMatch[['album_title']], on='uuid')



    def addAssetNameFromSmallestMemory(self):
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
                print("{}\n{} --> {}\n{}\n".format(
                        i+1,
                        s['start'].strftime(self.timecodeFormat)[:12],
                        s['end'].strftime(self.timecodeFormat)[:12],
                        s['text'].strftime(self.wallclockFormat)+self.circa*' (circa)'
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

