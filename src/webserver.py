import urllib.request
import os,random,time,signal
from flask import Flask, flash, request, redirect, url_for,render_template
from werkzeug.utils import secure_filename
from flask import send_from_directory
from datetime import datetime
from PIL import Image
import json
from inky.auto import auto
from gpiozero import Button
from PIL import ImageDraw,Image 
import generateInfo

# Gpio button pins from top to bottom
#5 == info
#6 == rotate clockwise
#16 == next image
#24 == reboot

ORIENTATION = 0
ADJUST_AR = False
CURRENT_IMAGE_INDEX = 0

# Get the current path
PATH = os.path.dirname(os.path.dirname(__file__))
print(PATH)
UPLOAD_FOLDER = os.path.join(PATH,"img")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg','webp'}
print(ALLOWED_EXTENSIONS)

# Check whether the specified path exists or not
pathExist = os.path.exists(os.path.join(PATH,"img"))

if(pathExist == False):
   os.makedirs(os.path.join(PATH,"img"))

#setup eink display and border
inky_display = auto(ask_user=True, verbose=True)
inky_display.set_border(inky_display.BLACK)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def getImageList():
    """Get sorted list of images in the img folder"""
    img_dir = os.path.join(PATH, "img")
    images = [f for f in os.listdir(img_dir) 
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
              and f != 'infoImage.png']
    images.sort()
    return images

def nextImage():
    """Advance to the next image in the folder"""
    global CURRENT_IMAGE_INDEX
    images = getImageList()
    if len(images) == 0:
        print("No images available")
        return
    CURRENT_IMAGE_INDEX = (CURRENT_IMAGE_INDEX + 1) % len(images)
    next_img = images[CURRENT_IMAGE_INDEX]
    print(f"Displaying image {CURRENT_IMAGE_INDEX + 1}/{len(images)}: {next_img}")
    updateEink(next_img, ORIENTATION, ADJUST_AR)

# Button handler functions for gpiozero
def button_a_pressed():
    print("--A-- Pressed: Show PiInk info")
    generateInfo.infoGen(inky_display.width,inky_display.height)
    updateEink("infoImage.png",0,"")

def button_b_pressed():
    print("--B-- Pressed: Rotate image clockwise")
    rotateImage(-90)

def button_c_pressed():
    print("--C-- Pressed: Next image")
    nextImage()

def button_d_pressed():
    print("--D-- Pressed: Reboot the Pi")
    os.system('sudo reboot')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    print("req ",request.files)    
    ADJUST_AR = False

    arSwitchCheck,horizontalOrientationRadioCheck,verticalOrientationRadioCheck = loadSettings()

    if horizontalOrientationRadioCheck == "checked":
        ORIENTATION = 0
    else:
        ORIENTATION = 1
    
    if arSwitchCheck == "checked":
        ADJUST_AR = True
    
    if request.method == 'POST':
        
        if 'file' in request.files or (request.form and request.form.get("submit") == "Upload Image"):
            file = request.files['file']
            print(file)
            if file and allowed_file(file.filename):
                # Images now accumulate instead of being deleted
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                filename = os.path.join(app.config['UPLOAD_FOLDER'],filename)

                updateEink(filename,ORIENTATION,ADJUST_AR)
                if(len(request.form) == 0):
                    return "File uploaded successfully", 200
            else:
                imageLink = request.form.getlist("text")[0]
                print(imageLink)
                try:
                    filename = imageLink.replace(":","").replace("/","")
                    filename = filename.split("?")[0]
                    print(filename)
                    urllib.request.urlretrieve(imageLink, os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    updateEink(filename,ORIENTATION,ADJUST_AR)
                except:
                    flash("Error: Unsupported Media or Invalid Link!")
                    return render_template('main.html')
                    
        if request.form["submit"] == 'Reboot':
            print("reboot")
            os.system("sudo reboot")
        
        if request.form["submit"] == 'Shutdown':
            print("shutdown")
            os.system("sudo shutdown")

        if request.form["submit"] == 'rotateImage':
            print("rotating image")
            rotateImage(-90)

        if request.form["submit"] == 'clearGhost':
            print("ghosting clear call!")
            clearScreen()

        if request.form["submit"] == 'Save Settings':
            if(request.form["frame_orientation"] == "Horizontal Orientation"):
                horizontalOrientationRadioCheck = "checked"
                verticalOrientationRadioCheck = ""
            else:
                horizontalOrientationRadioCheck = ""
                verticalOrientationRadioCheck = "checked"
            try:
                if request.form["adjust_ar"] == "true":
                    arSwitchCheck = "checked"
            except:
                arSwitchCheck = ""
                pass
            saveSettings(horizontalOrientationRadioCheck,verticalOrientationRadioCheck,arSwitchCheck)
            return render_template('main.html',horizontalOrientationRadioCheck = horizontalOrientationRadioCheck,verticalOrientationRadioCheck=verticalOrientationRadioCheck,arSwitchCheck=arSwitchCheck)       
    return render_template('main.html',horizontalOrientationRadioCheck = horizontalOrientationRadioCheck,verticalOrientationRadioCheck=verticalOrientationRadioCheck,arSwitchCheck=arSwitchCheck)

def loadSettings():
    horizontalOrient = ""
    verticalOrient = ""
    try:
        jsonFile = open(os.path.join(PATH,"config/settings.json"))
    except:
        saveSettings("","checked",'aria-checked="false"')
        jsonFile = open(os.path.join(PATH,"config/settings.json"))
    settingsData = json.load(jsonFile)
    jsonFile.close()
    if settingsData.get("orientation") == "Horizontal":
        horizontalOrient = "checked"
        verticalOrient = ""
    else:
        verticalOrient = "checked"
        horizontalOrient = ""
    return settingsData.get("adjust_aspect_ratio"),horizontalOrient,verticalOrient

def saveSettings(orientationHorizontal,orientationVertical,adjustAR):
    if orientationHorizontal == "checked":
        orientationSetting = "Horizontal"
    else:
        orientationSetting = "Vertical"
    jsonStr = {
        "orientation":orientationSetting,
        "adjust_aspect_ratio":adjustAR,
    }
    with open(os.path.join(PATH,"config/settings.json"), "w") as f:
        json.dump(jsonStr, f)

def updateEink(filename,orientation,adjustAR):
    with Image.open(os.path.join(PATH, "img/",filename)) as img:
        img = changeOrientation(img,orientation)
        img = adjustAspectRatio(img,adjustAR)    
        inky_display.set_image(img)
        inky_display.show()

def clearScreen():
    print("running ghost clear")
    img = Image.new(mode="RGB", size=(inky_display.width, inky_display.height),color=(255,255,255))
    clearImage = ImageDraw.Draw(img)
    inky_display.set_image(img)
    inky_display.show()
    images = getImageList()
    if images:
        updateEink(images[0],ORIENTATION,ADJUST_AR)

def changeOrientation(img,orientation):
    if orientation == 0:
        img = img.rotate(0)
    elif orientation == 1:
        img = img.rotate(90)
    return img

def adjustAspectRatio(img,adjustARBool):
    if adjustARBool:
        w = inky_display.width
        h = inky_display.height
        ratioWidth = w / img.width
        ratioHeight = h / img.height
        if ratioWidth < ratioHeight:
            resizedWidth = w
            resizedHeight = round(ratioWidth * img.height)
        else:
            resizedWidth = round(ratioHeight * img.width)
            resizedHeight = h
        imgResized = img.resize((resizedWidth, resizedHeight), Image.LANCZOS)
        background = Image.new('RGBA', (w, h), (0, 0, 0, 255))
        offset = (round((w - resizedWidth) / 2), round((h - resizedHeight) / 2))
        background.paste(imgResized, offset)
        img = background
    else:
        img = img.resize(inky_display.resolution)
    return img

def deleteImage():
    img_directory = os.path.join(PATH, "img")
    for filename in os.listdir(img_directory):
        fp = os.path.join(img_directory, filename)
        if os.path.isfile(fp):
            os.remove(fp)
            
def rotateImage(deg):
    images = getImageList()
    if not images:
        return
    current_img = images[CURRENT_IMAGE_INDEX % len(images)]
    with Image.open(os.path.join(PATH, "img/", current_img)) as img:
        img = img.rotate(deg, Image.NEAREST, expand=1)
        img.save(os.path.join(PATH, "img/", current_img))
        updateEink(current_img, ORIENTATION, ADJUST_AR)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

# Setup GPIO buttons using gpiozero
try:
    btn_a = Button(5, pull_up=True, bounce_time=0.25)
    btn_b = Button(6, pull_up=True, bounce_time=0.25)
    btn_c = Button(16, pull_up=True, bounce_time=0.25)
    btn_d = Button(24, pull_up=True, bounce_time=0.25)
    
    btn_a.when_pressed = button_a_pressed
    btn_b.when_pressed = button_b_pressed
    btn_c.when_pressed = button_c_pressed
    btn_d.when_pressed = button_d_pressed
    print("GPIO buttons initialized successfully")
except Exception as e:
    print(f"GPIO button setup failed: {e}")

if __name__ == '__main__':
    app.secret_key = str(random.randint(100000,999999))
    app.run(host="0.0.0.0",port=80)
