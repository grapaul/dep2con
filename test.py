from dep2con.dep2con import make_const

t_s = make_const("I saw a UFO in the backyard.",
                 lang = 'en', use_parser = True)

for dep2con in t_s:
    print(dep2con.sent_parse)
    print(dep2con.sent_dict)
    print(dep2con.sent_text)
    for i in dep2con.x_phrases:
        print(i)
