
import pickle
import cv2
import cvzone
import numpy as np
from cvzone.HandTrackingModule import HandDetector
import time

######################################
cam_id = 0
width, height = 1920, 1080
map_file_path = "C:\\Users\\vinayak shishodia\\PycharmProjects\\practicum\\polygon\\map.p"
countries_file_path = "C:\\Users\\vinayak shishodia\\PycharmProjects\\practicum\\polygon\\countries.p"

######################################

file_obj = open(map_file_path, 'rb')
map_points = pickle.load(file_obj)
file_obj.close()
print(f"Loaded map coordinates.")


if countries_file_path:
    file_obj = open(countries_file_path, 'rb')
    polygons = pickle.load(file_obj)
    file_obj.close()
    print(f"Loaded {len(polygons)} countries.")
else:
    polygons = []


cap = cv2.VideoCapture(cam_id)  # For Webcam
# Set the width and height of the webcam frame
cap.set(3, width)
cap.set(4, height)

counter = 0


detector = HandDetector(staticMode=False,
                        maxHands=1,
                        modelComplexity=1,
                        detectionCon=0.5,
                        minTrackCon=0.5)

questions = [["which country has the largest area?", "Russia"],
             ["which country has the largest population?", "China"],
             ["which country is a continent?", "Australia"],
             ["which country has the largest area?", "Russia"],
             ]

selected_country = None
country_entry_times = {}

counter_country = 0
counter_answer = 0
current_question = 0
start_counter = False

answer_color = (0, 0, 255)
total_score = 0


def warp_image(img, points, size=[1920, 1080]):

    pts1 = np.float32([points[0], points[1], points[2], points[3]])
    pts2 = np.float32([[0, 0], [size[0], 0], [0, size[1]], [size[0], size[1]]])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    imgOutput = cv2.warpPerspective(img, matrix, (size[0], size[1]))
    return imgOutput, matrix


def warp_single_point(point, matrix):

    point_homogeneous = np.array([[point[0], point[1], 1]], dtype=np.float32)

    # Apply the perspective transformation to the point
    point_homogeneous_transformed = np.dot(matrix, point_homogeneous.T).T

    # Convert back to non-homogeneous coordinates
    point_warped = point_homogeneous_transformed[0, :2] / point_homogeneous_transformed[0, 2]

    return point_warped


def get_finger_location(img, imgWarped):

    # Find hands in the current frame
    hands, img = detector.findHands(img, draw=False, flipType=True)
    # Check if any hands are detected
    if hands:
        # Information for the first hand detected
        hand1 = hands[0]  # Get the first hand detected
        indexFinger = hand1["lmList"][8][0:2]  # List of 21 landmarks for the first hand
        # cv2.circle(img,indexFinger,5,(255,0,255),cv2.FILLED)
        warped_point = warp_single_point(indexFinger, matrix)
        warped_point = int(warped_point[0]), int(warped_point[1])
        print(indexFinger, warped_point)
        cv2.circle(imgWarped, warped_point, 5, (255, 0, 0), cv2.FILLED)
    else:
        warped_point = None

    return warped_point


def inverse_warp_image(img, imgOverlay, map_points):

    # Convert map_points to NumPy array
    map_points = np.array(map_points, dtype=np.float32)

    # Define the destination points for the overlay image
    destination_points = np.array([[0, 0], [imgOverlay.shape[1] - 1, 0], [0, imgOverlay.shape[0] - 1],
                                   [imgOverlay.shape[1] - 1, imgOverlay.shape[0] - 1]], dtype=np.float32)

    # Calculate the perspective transform matrix
    M = cv2.getPerspectiveTransform(destination_points, map_points)

    # Warp the overlay image to fit the perspective of the original image
    warped_overlay = cv2.warpPerspective(imgOverlay, M, (img.shape[1], img.shape[0]))

    # Combine the original image with the warped overlay
    result = cv2.addWeighted(img, 1, warped_overlay, 0.65, 0, warped_overlay)

    return result


def create_overlay_image(polygons, warped_point, imgOverlay):


    country_selected = None
    # Set the duration threshold for making a country green
    green_duration_threshold = 2.0

    # loop through all the countries
    for polygon, name in polygons:
        polygon_np = np.array(polygon, np.int32).reshape((-1, 1, 2))
        result = cv2.pointPolygonTest(polygon_np, warped_point, False)
        if result >= 0:

            # If the country is not in the dictionary, add it with the current time
            if name not in country_entry_times:
                country_entry_times[name] = time.time()

            # Calculate the time the finger has spent in the country
            time_in_country = time.time() - country_entry_times[name]

            # If the time is greater than the threshold, make the country green
            if time_in_country >= green_duration_threshold:
                color = (0, 255, 0)  # Green color
                country_selected = name
            else:
                country_selected = None
                color = (255, 0, 255)  # Blue color
                # Draw an arc around the finger point based on elapsed time
                angle = int((time_in_country / green_duration_threshold) * 360)
                cv2.ellipse(imgOverlay, (warped_point[0], warped_point[1] - 100),
                            (50, 50), 0, 0, angle, color,
                            thickness=-1)

            cv2.polylines(imgOverlay, [np.array(polygon)], isClosed=True, color=color, thickness=2)
            cv2.fillPoly(imgOverlay, [np.array(polygon)], color)
            cvzone.putTextRect(imgOverlay, name, polygon[0], scale=1, thickness=1)
            cvzone.putTextRect(imgOverlay, name, (0, 100), scale=8, thickness=5)
        else:
            # If the finger is not in the country, remove it from the dictionary
            country_entry_times.pop(name, None)

    return imgOverlay, country_selected


def check_answer(name, current_question, img, total_score):
    global counter_answer, start_counter, answer_color

    if current_question == len(questions):
        cvzone.putTextRect(img, f"Your score is {total_score}/{len(questions)}", (620, 410), scale=5, thickness=5)
        return current_question, total_score

    if name != None:
        if name == questions[current_question][1]:
            start_counter = 'CORRECT'
            answer_color = (0, 255, 0)
        else:
            start_counter = 'WRONG'
            answer_color = (0, 0, 255)
    if start_counter:
        counter_answer += 1
        if counter_answer != 0:
            cvzone.putTextRect(img, start_counter, (800, 500), colorR=answer_color)
        if counter_answer == 70:
            counter_answer = 0
            current_question += 1
            if start_counter == "CORRECT":
                total_score += 1
            start_counter = False

    return current_question, total_score


while True:
    # Read a frame from the webcam
    success, img = cap.read()
    imgWarped, matrix = warp_image(img, map_points)
    imgOutput = img.copy()

    # Find the hand and its landmarks
    warped_point = get_finger_location(img, imgWarped)

    h, w, _ = imgWarped.shape
    imgOverlay = np.zeros((h, w, 3), dtype=np.uint8)

    selected_country = None
    if warped_point:
        imgOverlay, selected_country = create_overlay_image(polygons, warped_point, imgOverlay)
        imgOutput = inverse_warp_image(img, imgOverlay, map_points)

    # Display the current question
    if current_question != len(questions):
        cvzone.putTextRect(imgOutput, questions[current_question][0], (0, 100))
    current_question, total_score = check_answer(selected_country, current_question, imgOutput, total_score)



    cv2.imshow("Output Image", imgOutput)
    key = cv2.waitKey(1)