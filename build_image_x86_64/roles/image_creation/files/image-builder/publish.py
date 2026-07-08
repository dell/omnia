import subprocess
import boto3
import os
import tempfile
from datetime import datetime
# local imports
from utils import cmd, get_os
import logging

def _generate_labels(args):
    """Generate standard labels from configuration data"""
    labels = {}
    
    # Add any user-provided labels
    if 'labels' in args:
        labels.update(args['labels'])
    
    # Basic metadata
    labels['org.openchami.image.name'] = args['name']
    labels['org.openchami.image.type'] = args['layer_type']
    labels['org.openchami.image.parent'] = args['parent']
    if 'pkg_man' in args:
        labels['org.openchami.image.package-manager'] = args['pkg_man']
    
    # Version/tag information
    if isinstance(args['publish_tags'], list):
        labels['org.openchami.image.tags'] = ','.join(args['publish_tags'])
    else:
        labels['org.openchami.image.tags'] = args['publish_tags']
    
    # Build information
    labels['org.openchami.image.build-date'] = datetime.now().isoformat()
    
    # Repository information
    if 'repos' in args:
        repo_names = [repo['alias'] for repo in args['repos']]
        labels['org.openchami.image.repositories'] = ','.join(repo_names)
    
    # Package information
    if 'packages' in args:
        labels['org.openchami.image.packages'] = ','.join(args['packages'])
    
    if 'package_groups' in args:
        labels['org.openchami.image.package-groups'] = ','.join(args['package_groups'])
    
    return labels

def publish(cname, args):

    layer_name = args['name']
    publish_tags = args['publish_tags']
    if type(publish_tags) is not list:
        publish_tags = [publish_tags]
    if 'credentials' in args:
        credentials = args['credentials']
    parent = args['parent']
    
    # Generate standard labels
    print("Generating labels")
    labels = _generate_labels(args)
    print("Labels: " + str(labels))
    
    if args['publish_local']:
        print("Publishing to local storage")
        for tag in publish_tags:
            # Add labels if they exist
            if labels:
                label_args = []
                for key, value in labels.items():
                    label_args.extend(['--label', f'{key}={value}'])
                cmd(["buildah", "config"] + label_args + [cname], stderr_handler=logging.warn)
            cmd(["buildah","commit", cname, layer_name+':'+tag], stderr_handler=logging.warn)

    if args['publish_s3']:
        s3_prefix = args['s3_prefix']
        s3_bucket = args['s3_bucket']
        print("Publishing to S3 at " + s3_bucket)
        for tag in publish_tags:
            s3_push(cname, layer_name, credentials, tag, s3_prefix, s3_bucket)

    if args['publish_registry']:
        registry_opts = args['registry_opts_push']
        publish_dest = args['publish_registry']
        print("Publishing to registry at " + publish_dest)
        image_name = layer_name+':'+publish_tags[0]
        # Add labels if they exist
        if labels:
            label_args = []
            for key, value in labels.items():
                label_args.extend(['--label', f'{key}={value}'])
            cmd(["buildah", "config"] + label_args + [cname], stderr_handler=logging.warn)
        cmd(["buildah", "commit", cname, image_name], stderr_handler=logging.warn)
        for tag in publish_tags:
            cmd(["buildah", "tag", image_name, layer_name+':'+tag], stderr_handler=logging.warn)
            registry_push(layer_name, registry_opts, tag, publish_dest)

    # Clean up
    cmd(["buildah", "rm", cname], stderr_handler=logging.warn)
    if not args['publish_local'] and args['publish_registry']:
        for tag in publish_tags:
            cmd(["buildah","rmi", layer_name+':'+tag], stderr_handler=logging.warn)
    if not parent == "scratch":
        cmd(["buildah", "rmi", parent], stderr_handler=logging.warn)

def push_file(fname, kname, s3, bucket_name):
    print("Pushing " + fname + " as " + kname + " to " + bucket_name)

    bucket = s3.Bucket(bucket_name)
    bucket.upload_file(Filename=fname,Key=kname)

def squash_image(mname, tmpdir):
    print("squashing container image")
    args = ["mksquashfs"]
    args.append(mname)
    args.append(tmpdir + "/rootfs")

    process = subprocess.run(args,
            stdout=subprocess.PIPE,
            universal_newlines=True)
    # if verbose:
    #     print(process.stdout)

def s3_push(cname, layer_name, credentials, publish_tags, s3_prefix, s3_bucket):

    def buildah_handler(line):
            out.append(line)
    out = []
    cmd(["buildah", "mount", cname],stdout_handler = buildah_handler)
    mdir = out[0]
   
    print(mdir)

    # Get s3 resource set
    s3 = boto3.resource('s3',
                    endpoint_url=credentials['endpoint_url'],
                    aws_access_key_id=credentials['access_key'],
                    aws_secret_access_key=credentials['secret_key'],
                    verify=False, use_ssl=False)

    # Set initrd to be blank to act as sentinel in case no intrds are found
    initrd = ''

    # Iterate over everything in /lib/modules and use the first initramfs or
    # initrd found.
    #
    # TODO: Be smarter about chooding initramfs. This code only uses the first
    #       available one.
    modules_dir = mdir+'/lib/modules/'
    if not os.path.isdir(modules_dir):
        logging.warning(f'No kernel modules directory found at {modules_dir}, skipping initramfs/vmlinuz upload')
        return
    kvers = os.listdir(modules_dir)
    logging.info(f'Available kernel versions: {kvers}')
    for kver in kvers:
        if os.path.isfile(mdir+'/boot/initramfs-'+kver+'.img'):
            initrd='initramfs-'+kver+'.img'
            logging.info(f'Found initrd: {initrd}')
        elif os.path.isfile(mdir+'/boot/initrd-'+kver):
            initrd='initrd-'+kver
            logging.info(f'Found initrd: {initrd}')
        elif os.path.isfile(mdir+'/boot/initrd.img-'+kver):
            initrd='initrd.img-'+kver
            logging.info(f'Found initrd (Ubuntu): {initrd}')
        else:
            logging.warn(f'No initramfs found for {kver}, moving to next')
            continue
        vmlinuz='vmlinuz-'+kver
        break

    # If no initramfses are found, return an error
    #
    # TODO: Should we continue without uploading if this fails?
    if initrd == '':
        raise Exception('No initramfs or initrd found in /boot for any of the available kernel versions')

    with tempfile.TemporaryDirectory() as tmpdir:
        squash_image(mdir, tmpdir)
        image_name = s3_prefix+get_os(mdir)+'-'+layer_name+'-'+publish_tags
        print("Image Name: " + image_name)
        print("initramfs: " + initrd )
        print("vmlinuz: " + vmlinuz )
        push_file(mdir+'/boot/'+initrd, 'efi-images/' + s3_prefix + initrd, s3, s3_bucket)
        push_file(mdir+'/boot/'+vmlinuz, 'efi-images/' + s3_prefix + vmlinuz, s3, s3_bucket)
        push_file(tmpdir + '/rootfs', image_name, s3, s3_bucket)

def registry_push(layer_name, registry_opts, publish_tags, registry_endpoint):

    image_name = layer_name+':'+publish_tags
    print("pushing layer " + layer_name + " to " + registry_endpoint +'/'+image_name)
    args = registry_opts + [image_name, registry_endpoint +'/'+image_name]
    cmd(["buildah", "push"] + args, stderr_handler=logging.warn)
