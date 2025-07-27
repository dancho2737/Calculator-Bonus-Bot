import random

# Словари для перевода чисел
UNITS = ["", "бир", "эки", "үч", "төрт", "беш", "алты", "жети", "сегиз", "тогуз"]
TENS = ["", "он", "жыйырма", "отуз", "кырк", "элүү", "алтымыш", "жетимиш", "сексен", "токсон"]
HUNDREDS = ["", "жүз", "эки жүз", "үч жүз", "төрт жүз", "беш жүз", "алты жүз", "жети жүз", "сегиз жүз", "тогуз жүз"]
THOUSANDS = ["", "миң", "эки миң", "үч миң", "төрт миң", "беш миң", "алты миң", "жети миң", "сегиз миң", "тогуз миң"]

def number_to_kg(n: int) -> str:
    if n == 0:
        return "нөл"
    parts = []
    thousands = n // 1000
    if thousands:
        parts.append(THOUSANDS[thousands])
    hundreds = (n % 1000) // 100
    if hundreds:
        parts.append(HUNDREDS[hundreds])
    tens = (n % 100) // 10
    units = n % 10
    if tens:
        parts.append(TENS[tens])
    if units:
        parts.append(UNITS[units])
    return " ".join(parts).strip()

def get_random_number_question() -> tuple[str, int]:
    number = random.randint(10, 50000)
    return number_to_kg(number), number  # Возвращаем строку на кыргызском и само число

