@bot.command()
async def scnew(ctx, *arg):
    if ctx.message.author.id == owner_userid:
        try:
            type_id = int(arg[0])
        except:
            if arg[0] == 'channel':
                type_id = 0
            elif arg[0] == 'emote':
                type_id = 2
            elif arg[0] == 'aemote':
                type_id = 3
            elif arg[0] == 'role':
                type_id = 4
            else:
                type_id = 1
        sc_name = ' '.join(arg[2:])
        sc_id = int(arg[1])
        mydb.new_shortcut(sc_name, type_id, sc_id)
        await ctx.send(f"Added {sc_name} as type {type_id} shortcut.")

@bot.command()
async def scdel(ctx, *arg):
    if ctx.message.author.id == owner_userid:
        argstr = ' '.join(arg)
        scstr = mydb.get_shortcut(argstr)
        mydb.delete_shortcut(argstr)
        await ctx.send(f"Deleted shortcut `{scstr}`.")

@bot.command()
async def scall(ctx):
    if ctx.message.author.id == owner_userid:
        embed = discord.Embed()
        embed.title = 'All Shortcuts'
        tup_list = mydb.get_all_shortcuts()
        field_lists = [[], [], []]
        for tup in tup_list:
            field_lists[0].append(tup[0])
            field_lists[1].append(str(tup[1]))
            field_lists[2].append(str(tup[2]))
        for name, field_list in zip(['Name', 'Type', 'id'], field_lists):
            embed.add_field(name=name, value='\n'.join(field_list))
        await ctx.send(embed = embed)
