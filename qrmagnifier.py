import ui
from io import BytesIO
from objc_util import (
    ObjCInstance,
    ObjCClass,
    on_main_thread,
    create_objc_class,
    CGRect,
    CGSize,
    CGPoint,
    c_void_p,
    c,
)
import qrcode
import sound
import ctypes

# Create a dispatch queue using the C function
libc = ctypes.CDLL(None)
dispatch_queue_create = libc.dispatch_queue_create
dispatch_queue_create.argtypes = [ctypes.c_char_p, c_void_p]
dispatch_queue_create.restype = c_void_p

dispatch_get_current_queue = c.dispatch_get_current_queue
dispatch_get_current_queue.restype = c_void_p


def captureOutput_didOutputMetadataObjects_fromConnection_(
    _self, _cmd, _output, _metadata_objects, _conn
):
    print("captureOutput_didOutputMetadataObjects_fromConnection_")
    objects = ObjCInstance(_metadata_objects)
    for obj in objects:
        if str(obj.type()) == "org.iso.QRCode":
            s = str(obj.stringValue())
            sound.play_effect("digital:PowerUp7")
            scanview.session.stopRunning()
            nav.push_view(QRView(s))
            break


# Create MetadataDelegate class
MetadataDelegate = create_objc_class(
    "MetadataDelegate",
    methods=[captureOutput_didOutputMetadataObjects_fromConnection_],
    protocols=["AVCaptureMetadataOutputObjectsDelegate"],
)


# Define a class to handle the QR code scanning
class QRScannerView(ui.View):
    def __init__(self):
        self.bg_color = "black"
        self.scanning = True
        self.setup_camera()

    @on_main_thread
    def setup_camera(self):
        # Initialize AVCaptureSession
        self.session = ObjCClass("AVCaptureSession").alloc().init()

        # Get the device's default video capture device (camera)
        self.device = ObjCClass("AVCaptureDevice").defaultDeviceWithMediaType_("vide")
        self.input = ObjCClass("AVCaptureDeviceInput").deviceInputWithDevice_error_(
            self.device, None
        )
        if self.session.canAddInput_(self.input):
            self.session.addInput_(self.input)

        # Set up output for metadata (QR codes)
        self.output = ObjCClass("AVCaptureMetadataOutput").alloc().init()

        # Create a new dispatch queue
        queue_name = b"qr_code_queue"
        # self.queue = dispatch_queue_create(queue_name, None)
        self.queue = ObjCInstance(dispatch_get_current_queue())

        # Create a delegate instance and set it for the metadata output
        delegate = MetadataDelegate.new()
        self.output.setMetadataObjectsDelegate_queue_(delegate, self.queue)
        self.session.addOutput_(self.output)

        # Set metadata object types to QR code
        self.output.setMetadataObjectTypes_(["org.iso.QRCode"])

        # Create video preview layer
        self.previewLayer = (
            ObjCClass("AVCaptureVideoPreviewLayer")
            .alloc()
            .initWithSession_(self.session)
        )
        self.previewLayer.videoGravity = "AVLayerVideoGravityResizeAspectFill"

        # Add the preview layer to the view
        self.layer = ObjCInstance(self.objc_instance.layer())
        self.layer.addSublayer_(self.previewLayer)

        # Start the session
        self.session.startRunning()

    def will_close(self):
        # Stop the session when the view is closed
        if self.session.isRunning():
            self.session.stopRunning()
        self.session.release()
        self.previewLayer.removeFromSuperlayer()

    def updateVideoOrientation(self):
        connection = self.previewLayer.connection()
        if connection.isVideoOrientationSupported():
            if self.width > self.height:
                connection.setVideoOrientation_(3)  # Landscape
            else:
                connection.setVideoOrientation_(1)  # Portrait

    def layout(self):
        self.previewLayer.frame = CGRect(CGPoint(0, 0), CGSize(self.width, self.height))
        self.updateVideoOrientation()
        if not self.session.isRunning():
            self.session.startRunning()

    def touch_began(self, touch):
        if not self.session.isRunning():
            self.session.startRunning()
        else:
            self.session.stopRunning()


class QRView(ui.View):
    def __init__(self, qr_string):
        self.bg_color = "white"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_string)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # PILイメージをバイトデータに変換
        with BytesIO() as b:
            qr_image.save(b, format="PNG")
            img_data = b.getvalue()

        self.image_view = ui.ImageView()
        self.image_view.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        self.image_view.image = ui.Image.from_data(img_data)
        self.add_subview(self.image_view)

        self.label = ui.Label()
        self.label.text = "ガウラミライカイギ 2024.10.23"
        self.label.font = ("Hiragino Maru Gothic ProN", 40)
        self.label.flex = "LRTB"
        self.label.width = self.width
        self.label.alignment = ui.ALIGN_CENTER
        self.add_subview(self.label)

    def layout(self):
        print(self.bounds)
        side_length = min(self.width, self.height) * 0.9
        self.label.width = self.width
        self.label.center = (self.width / 2, 60)
        self.label
        self.image_view.frame = (
            self.width / 2 - side_length / 2,
            self.height / 2 - side_length / 2,
            side_length,
            side_length,
        )

    # When tapped, close self
    def touch_began(self, touch):
        nav.pop_view()


@on_main_thread
def main():
    global nav, scanview
    scanview = QRScannerView()
    nav = ui.NavigationView(scanview)
    nav.navigation_bar_hidden = True
    nav.present("fullscreen", hide_title_bar=True)


main()
