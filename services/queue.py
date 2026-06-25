current_index = 0


def get_next_employee(employees):
    global current_index

    if not employees:
        return None

    emp = employees[current_index]

    current_index += 1

    if current_index >= len(employees):
        current_index = 0

    return emp