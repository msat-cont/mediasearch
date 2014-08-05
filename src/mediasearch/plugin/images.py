#!/usr/bin/env python
#
# Mediasearch
# Performs media hashing, hash storage and (perceptual) similarity search
#

#import sys, os, logging, datetime
#import json, tempfile, urllib2
#import re, operator
#from mediasearch.algs.methods import MediaHashMethods
#from mediasearch.utils.sync import synchronizer

try:
    unicode()
except:
    unicode = str

class MediaImage(object):
    known_media_types = {'image' : ['png', 'jpg', 'jpeg', 'pjpeg', 'gif', 'bmp', 'x-ms-bmp', 'tiff']}
    known_url_types = ['file', 'http', 'https']

    def __init__(self, base_media_path='/', tmp_dir='/tmp'):
        #self.base_media_path = base_media_path
        #self.tmp_dir = tmp_dir
        #self.hash_methods_holder = MediaHashMethods()
        #self.hash_methods = self.hash_methods_holder.get_methods()
        pass

    def _save_take_media_file(self, media_path, media_type):
        # take downloaded/provided file
        # extract exif data, if possible
        # put into grid_fs
        from pymongo import MongoClient
        import gridfs

        import pyexiv2
        import fractions
        #path = '/home/mds/Downloads/fabric/imgs/other/25973335.jpg'
        metadata = pyexiv2.ImageMetadata(path)
        metadata.read()

        location = self._extract_gps_coordinates(metadata)
        timestamps = self._extract_timestamps(metadata)

        db_grid = MongoClient().gridfs_example
        fs_grid = gridfs.GridFS(db_grid)

    def _save_media_file(self, fs_grid, media_path, media_type, uid, feed_name):
        CHUNK_LENGTH = 8192
        MEDIA_FORM = 'received'

        fid = None
        correct = True

        metadata = {
            'feed': feed_name,
            'form': MEDIA_FORM,
        }

        with fs_grid.new_file(
            filename = uid,
            content_type = media_type,
            metadata = metadata
        ) as fp:
            fid = fp._id
            try:
                mfh = open(media_path)
                while True:
                    mdata = mfh.read(CHUNK_LENGTH)
                    if not mdata:
                        break
                    fp.write(mdata)
                mfh.close()

            except Exception as exc:
                correct = False

        if not correct:
            try:
                fs.delete(fid)
            except Exception as exc:
                pass

        if correct:
            return fid
        return None

    def _save_media_info(self, db, media_type, uid, feed_name, exif_data, thumbnail, fid, gps, timestamps):
        COLL_NAME = 'media_info'

        media_data = {
            'uid': uid,
            'type': media_type,
            'feed': feed_name,
            'exif': exif_data,
            'gps': gps,
            'media_created': timestamps['created'],
            'media_updated': timestamps['updated'],
            'fid': fid,
            'thumbnail': thumbnail,
        }

        coll = db[COLL_NAME]
        coll.save(media_data)


    def _create_thumbnail(self, media_path, media_type):
        # if media_type not in IMAGE_MEDIA_TYPES: return None

        import os, tempfile
        import Image

        MAXWIDTH = 150
        MAXHEIGHT = 150
        THUMB_FILE_NAME = 'thumbnail.jpg'

        try:
            tmp_dir_path = tempfile.mkdtemp()
            tmp_outfile = os.path.join(tmp_dir_path, THUMB_FILE_NAME)

            im = Image.open(media_path)

            im_size = im.size()
            ratio_width = MAXWIDTH / im_size[0]
            ratio_height = MAXHEIGHT / im_size[1]
            ratio = (ratio_width, ratio_height)
            th_size = (ratio*im_size[0], ratio*im_size[1])

            im.thumbnail(th_size, Image.ANTIALIAS)
            im.save(tmp_outfile, 'JPEG')

            fh_thumb = open(tmp_outfile)
            thumb = fh_thumb.read()
            fh_thumb.close()

            os.unlink(tmp_outfile)
            os.rmdir(tmp_dir_path)

            return thumb
        except:
            return None


    def _extract_timestamps(self, metadata):

        keys_created = ['Exif.Photo.DateTimeOriginal', 'Exif.Photo.DateTimeDigitized']
        keys_modified = ['Xmp.xmp.ModifyDate', 'Exif.Image.DateTime']

        values = {'created': None, 'modified': None}

        val_created = None
        for one_key in keys_created:
            try:
                one_val = metadata.get(one_key)
                if one_val:
                    one_val = one_val.value.isoformat()
                    if not val_created:
                        val_created = one_val
                    else:
                        if one_val < val_created:
                            val_created = one_val
            except Exception as exc:
                continue

        val_modified = None
        for one_key in keys_modified:
            try:
                one_val = metadata.get(one_key)
                if one_val:
                    one_val = one_val.value.isoformat()
                    if not val_modified:
                        val_modified = one_val
                    else:
                        if one_val > val_modified:
                            val_modified = one_val
            except Exception as exc:
                continue

        values = {'created': val_created, 'modified': val_modified}

        return values

    def _extract_gps_coordinates(self, metadata):


        '''
        from PIL import Image
        from PIL import ExifTags

        path = '/home/mds/Downloads/fabric/imgs/other/25973335.jpg'
        img = Image.open(path)
        exif = {ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS}
        exif['GPSInfo']
        #{0: (2, 2, 0, 0), 1: 'N', 2: ((50, 1), (5, 1), (34559, 1670)), 3: 'E', 4: ((14, 1), (25, 1), (22066, 1321)), 5: 0, 6: (0, 1), 7: ((9, 1), (8, 1), (55, 1)), 8: '0', 18: 'WGS-84', 29: '2009:05:09'}
        '''

        #for key in metadata: print(str(key) + ':\t' + str(metadata[key].raw_value))

        values = {'latitude': None, 'longitude': None}

        gps_result = [None, None]

        # 50.089N, 14.421E
        try:
            gps_source = [metadata.get('Exif.GPSInfo.GPSLatitude'), metadata.get('Exif.GPSInfo.GPSLongitude')]
            for idx in range(2):
                if not gps_source[idx]:
                    continue

                one_gps_list = gps_source[idx].value
                if type(one_gps_list) is not pyexiv2.utils.NotifyingList:
                    continue
                if 1 > len(one_gps_list):
                    continue

                one_gps_deg = one_gps_list[0]
                if type(one_gps_deg) is not fractions.Fraction:
                    continue
                one_gps_value = float(one_gps_deg.numerator) / float(one_gps_deg.denominator)

                if 2 <= len(one_gps_list):
                    one_gps_min = one_gps_list[1]
                    if type(one_gps_min) is not fractions.Fraction:
                        continue
                    one_gps_value += float(one_gps_min.numerator) / (60.0 * float(one_gps_min.denominator))

                if 3 <= len(one_gps_list):
                    one_gps_sec = one_gps_list[2]
                    if type(one_gps_sec) is not fractions.Fraction:
                        continue
                    one_gps_value += float(one_gps_sec.numerator) / (3600.0 * float(one_gps_sec.denominator))

                gps_result[idx] = one_gps_value

            if gps_result[0]:
                lat_dir = metadata.get('Exif.GPSInfo.GPSLatitudeRef')
                if lat_dir:
                    lat_dir = lat_dir.value
                if lat_dir not in ('N', 'n', 'S', 's'):
                    raise Exception('unknow latitude hemisphere specifier')

                if lat_dir in ('S', 's'):
                    gps_result[0] *= -1.0

            if gps_result[1]:
                lat_dir = metadata.get('Exif.GPSInfo.GPSLongitudeRef')
                if lat_dir:
                    lat_dir = lat_dir.value
                if lat_dir not in ('W', 'w', 'E', 'e'):
                    raise Exception('unknow longitude hemisphere specifier')

                if lat_dir in ('W', 'w'):
                    gps_result[1] *= -1.0

        except Exception as exc:
            return values

        if gps_result[0]:
            values['latitude'] = gps_result[0]
        if gps_result[0] and gps_result[1]:
            values['longitude'] = gps_result[1]

        return values


        '''

Exif.Image.GPSTag:	614
Exif.GPSInfo.GPSVersionID:	2 2 0 0
Exif.GPSInfo.GPSLatitudeRef:	N
Exif.GPSInfo.GPSLatitude:	50/1 5/1 34559/1670
Exif.GPSInfo.GPSLongitudeRef:	E
Exif.GPSInfo.GPSLongitude:	14/1 25/1 22066/1321
Exif.GPSInfo.GPSAltitudeRef:	0
Exif.GPSInfo.GPSAltitude:	0/1
Exif.GPSInfo.GPSTimeStamp:	9/1 8/1 55/1
Exif.GPSInfo.GPSSatellites:	0
Exif.GPSInfo.GPSMapDatum:	WGS-84
Exif.GPSInfo.GPSDateStamp:	2009:05:09


Xmp.exif.GPSVersionID:	2.2.0.0
Xmp.exif.GPSLatitude:	50,5.3449N
Xmp.exif.GPSLongitude:	14,25.2784E
Xmp.exif.GPSAltitudeRef:	0
Xmp.exif.GPSAltitude:	0/1
Xmp.exif.GPSTimeStamp:	2009-05-09T09:08:55Z
Xmp.exif.GPSSatellites:	0
Xmp.exif.GPSMapDatum:	WGS-84

        '''




        '''
http://www.digital-photo-secrets.com/tip/1401/how-do-you-find-the-gps-coordinates-of-your-photos/
http://www.panoramio.com/photo/25973335
http://static.panoramio.com/photos/original/25973335.jpg
http://regex.info/exif.cgi?b=3&referer=http%3A%2F%2Fstatic.panoramio.com%2Fphotos%2Foriginal%2F25973335.jpg&imgurl=http%3A%2F%2Fstatic.panoramio.com%2Fphotos%2Foriginal%2F25973335.jpg



http://stackoverflow.com/questions/4764932/in-python-how-do-i-read-the-exif-data-for-an-image
http://stackoverflow.com/questions/19817305/reading-exif-data-of-a-jpeg-using-python
https://code.google.com/p/pexif/
https://pypi.python.org/pypi/ExifRead
http://eran.sandler.co.il/2011/05/20/extract-gps-latitude-and-longitude-data-from-exif-using-python-imaging-library-pil/
https://dpk.net/2013/02/21/simple-python-script-to-strip-exif-data-from-a-jpeg/
http://tilloy.net/dev/pyexiv2/api.html
http://sourceforge.net/projects/exif-py/
http://www.endlesslycurious.com/2011/05/11/extracting-image-exif-data-with-python/
http://tilloy.net/dev/pyexiv2/tutorial.html


        '''




        '''
        media_type_parts = str(media_type).strip().split('/')
        if 2 != len(media_type_parts):
            return False
        if not media_type_parts[0] in self.known_media_types:
            logging.warning('unknown media class: ' + str(media_type_parts[0]))
            return False
        if not media_type_parts[1] in self.known_media_types[media_type_parts[0]]:
            logging.warning('unknown media type: ' + str(media_type))
            return False

        url_type = None
        for test_url_type in self.known_url_types:
            if media_url.startswith(test_url_type + ':'):
                url_type = test_url_type
                break

        if not url_type:
            logging.warning('unknown type of media url: ' + str(media_url))
            return False

        remove_img = False
        if 'file' != url_type:
            local_img_path = self._ext_download_media_file(media_url)
            if not local_img_path:
                return None
            remove_img = True
        else:
            local_img_path = media_url[len('file:'):]
            if local_img_path.startswith('//'):
                local_img_path = local_img_path[len('//'):]

        if not local_img_path.startswith('/'):
            local_img_path = os.path.join(self.base_media_path, local_img_path)

        media_hash = self._alg_create_hashes(local_img_path, media_type_parts[1])

        if remove_img:
            try:
                os.unlink(local_img_path)
            except:
                pass

        return media_hash
        '''
