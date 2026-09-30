from notifications import send_welcome_email

result = send_welcome_email(
    recipient_email="bikayshaw07@gmail.com",
    student_name="Test Student",
    student_id=1001,
)

if result:
    print("SUCCESS: Welcome email sent!")
else:
    print("FAILED: Check the terminal error messages.")