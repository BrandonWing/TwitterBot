'''
Created on May 24, 2017
A twitter bot for a friend that requested that it spew
out trash anime pictures for him. 
Also used to display knowledge in python3 and basic knowledge of
sqlite3.
@author: brand
'''


import time, random, sys, urllib.request, sqlite3, requests, os
from bs4 import BeautifulSoup
from _sqlite3 import Cursor
from glob import glob
from pixivpy3 import *



class Bot:
    def __init__(self):

        #set up database opening
        self._conn = sqlite3.connect('animeDatabase.db')
        self._conn.row_factory = lambda cursor, row: row[0]
        self._c = self._conn.cursor()
        
        #Set up twitter authentification
        import tweepy
        self.CONSUMER_KEY = 'StGmdnj5lewJYr61CpQYxQUSZ'
        self.CONSUMER_SECRET = 'iuGNtOk4Qz0Yx4bwemCcxgoDBWUznMIbixg71WygSMLVdz9EEU'
        self.ACCESS_KEY = '707653398-trUN1sut0onVSiTP9zl80OPskiZDAxWWXfBhE0hx'
        self.ACCESS_SECRET = 'LmbKx48NAfqwdZZ1qAiOImiPjcFivEIn2V33OcgyRL2HB'
        self.auth = tweepy.OAuthHandler(self.CONSUMER_KEY, self.CONSUMER_SECRET)
        self.auth.set_access_token(self.ACCESS_KEY, self.ACCESS_SECRET)
        self.api = tweepy.API(self.auth)
        
        #set pixiv api up
        self.pixiv = AppPixivAPI()
        
        #create the database
        self._create_update_database()
    
    
    
    #updates the table, checking first to see if the link already exists in the table, then inserting
    def _update_table(self, table_name, link):
        query = "SELECT rowid FROM {} WHERE link = ?".format(table_name)
        self._c.execute(query, (link,))
        data = self._c.fetchall()
        
        #if no mathches were found, the length will be 0 and we can insert
        if len(data) == 0:
            
            if table_name == 'shuushuu':
                linknumber = link[40:46]
                newUrl = 'http://e-shuushuu.net/image/' + linknumber
                url = urllib.request.urlopen(newUrl)
                soup = BeautifulSoup(url, "html.parser")
                try:
                    tag = soup.find(id = "quicktag2_" + linknumber)
                    tagstring = ""
                    for href in tag.findAll('a'):
                        tagstring += "~" + href.string + "~"
                    
                except:
                    tagstring = "None"
                print(tagstring)
                query = 'INSERT INTO {} VALUES (?, "False", ?)'.format(table_name)
                self._c.execute(query, (link,tagstring))
                self._conn.commit()
                print('Inserting {}'.format(link))
                
            else:
                query = 'INSERT INTO {} VALUES (?, "False", "None")'.format(table_name)
                self._c.execute(query, (link,))
                self._conn.commit()
                print('Inserting {}'.format(link))
        
        #return break to be used by other functions to stop loops
        else:
            print('No more to insert on {}'.format(link))
            return 'Break' 
            
            
    #Set to get a mass amount of pics initially to be put into datatable
    #Will be used also to update table after initial creation
    def _get_shuushuu_pic_links(self):
        
        #Goes through 2000 pages from the website to get the picture links
        for i in range(1, 2000):
            wrong_in_a_row = 0
            url = urllib.request.urlopen('http://e-shuushuu.net/?page={}'.format(str(i)))
            soup = BeautifulSoup(url, "html.parser")
            class_list = soup.find_all('a', class_ = 'thumb_image')
            for class_ in class_list:
                image = class_.find('img')['src']
                image = image.replace('thumbs/', "")
                
                #certain images that were not wanted had the word common in the link
                if ('common' not in image):
                    imageURL = 'http://e-shuushuu.net' + image
                    
                    #SHuushuu has a weird bug where it will repeat the last pic on one page on the next page over,
                    #wrong_in_a row variable checks for this. If it happens more than 5 times on a single page, it means
                    #we have downloaded all after it.
                    if self._update_table('shuushuu', imageURL) == 'Break':
                        wrong_in_a_row += 1
                        if wrong_in_a_row == 5:
                            return

            
            
    #Creates initial database to hold pixiv and shuushuu links to pictures
    #Will then afterward be used to update the database daily with new links             
    def _create_update_database(self):
        
        try:
            self._c.execute('CREATE TABLE IF NOT EXISTS shuushuu (link TEXT, usage TEXT, tag TEXT)')
            self._conn.commit()
            self._get_shuushuu_pic_links()
        except:
            print('Shuushuu is down')
        
        
    
    #In case working on raspberry pi, used to view the datatables and contents
    #...tfw no db viewer on pi..
    def check_database(self, table):
        query = "SELECT * FROM {}".format(table)
        self._c.execute(query)
        rows = self._c.fetchall()
        for row in rows:
            print (row)
        
    #Download pic to folder to be uploaded to twitter. This got sketchy with shuushuu's links
    def _download_pics(self, link):
        print(link)
        #All shuushuu links have jpeg in them
        if 'jpeg' in link:
            
            #This one is weird. The ShuuShuu website sent back all links ending with jpeg
            #However, multiple hours and errors later, I found that some were actually png
            #Could not figure out the pattern or cause of why this occured, so I created
            #a weird spaghetti code work around to basically download it in both formats.
            #Effectively, one will work, while the other doesn't.
            try:
                img_data = requests.get(link).content
                link = link.replace('jpeg', 'png')
                img_data2= requests.get(link).content
                with open('pic.jpeg', 'wb') as handler:
                    handler.write(img_data)
                    handler.close()
            
                with open('pic.png', 'wb') as handler:
                    handler.write(img_data2)
                    handler.close()
            
                #After both formats are downloaded, one will basically have no data and can be deleted
                if os.path.getsize('pic.jpeg') < 5000: #5kb effectively
                    os.remove('pic.jpeg')
                    return 'pic.png'
                else:
                    os.remove('pic.png')
                    return 'pic.jpeg'
            except:
                link = self._choose_pic[0]
                return self._download_pics(link)
        
        
            
    
    #Chooses a picture link from the database at random, changing usage to True to ensure no repeats
    def _choose_pic(self):
        #66% chance using shuushuu table (seeing that it has more), 33% for zerochan
        choice = random.randint(1, 5)
        if choice < 3:
            key = 'shuushuu'
        else:
            key = 'zerochan'
        #choose a random rowid to select link from. 
        query = 'SELECT * FROM {}'.format(key)
        self._c.execute(query)
        results = self._c.fetchall()
        row_id = random.randint(1, len(results))
        query = 'SELECT usage from {} WHERE rowid = ?'.format(key)
        self._c.execute(query, (row_id,))
        usage = self._c.fetchone()
        
        #If the selected link has already been used, recursive repeat function until unused link is found
        if usage == 'True':
            return self._choose_pic()
        
        else:
            #There must be a way to do multiple sql commands at once...
            query = 'SELECT link from {} WHERE rowid = ?'.format(key)
            self._c.execute(query, (row_id,))
            link = self._c.fetchone()
            
            query = 'SELECT tag from {} WHERE link = ?'.format(key)
            self._c.execute(query, (link,))
            tag = self._c.fetchone()
            
            query = 'UPDATE {} SET usage = "True" WHERE rowid = ?'.format(key)
            self._c.execute(query, (row_id,))
            self._conn.commit()
            print(tag)
            return (link, tag)
        
        
    
    #Found a 10,000 picture anime wallpaper download online, figured I'd use some
    #Obviously this function won't work unless you have this foler on your computer
    def _choose_wallpaper(self):
        #gets list of all directories in wallpaper folder (they were organized, seperated into folders)
        directory_list = glob("Anime/*/")
        directory_index = random.randint(0, len(directory_list) - 1)
        
        #chooses a random directory
        anime_choice = directory_list[directory_index]
        anime_choice = str(glob(anime_choice)[0])
        anime_choice = anime_choice.replace('\\\\', '/') + '*.png' #linux uses /, not \
        
        #gets list of all pictures in the chosen directory
        anime_pic_list = glob(anime_choice)
        for pic in glob(anime_choice.replace('png', 'jpg')):
            anime_pic_list.append(pic)
            
        #some spaghetti code to get a picture location and the name 
        anime_choice_pic = anime_pic_list[random.randint(0, len(anime_pic_list)) - 1] #random index from list
        
        #a string to hold the title of the wallpaper, since they were so nicely organized
        anime_choice_string = anime_choice.replace('Anime/', 'anime ') 
        anime_choice_string = anime_choice_string.replace('/*.png', '')
        anime_choice_string = anime_choice_string.replace('/*.jpg', '')
        return [anime_choice_pic, anime_choice_string]
    
    
    #Deletes a picture after it has been used
    def _delete_pic(self, directory):
        try:
            print ('Deleting ' + directory)
            os.remove(directory)
        except:
            print("Nothing to delete.")
        
    #Every 30 minutes chooses a picture and uploads. Every two hours, a wallpaper. Every day, update.
    def mainloop(self):
        next_call = time.time()
        wallpaper_timer = 1
        update_timer = 1
        while True:
            
            #Mainloop will run 48 times a day. Therefore, update on 48th time = next day
            if update_timer == 72:
                self._create_update_database()
                update_timer = 1
                print('I updated myself')
            
            #Mainloops runs twice an hour. Therefore, four loops = 2 hours = wallpaper
            if wallpaper_timer == 4:
                
                try: #only had one time when it bugged on wallpapers, but try catch to be safe
                    walltuple = self._choose_wallpaper()
                    self.api.update_with_media(walltuple[0], status = "Here's a wallpaper from the " + walltuple[1] + '!')
                    print('I put up a wallpaper')
                    wallpaper_timer = 1
                    self._delete_pic(walltuple[0])
                    print('Just deleted ' + walltuple[0])
                    next_call += 1200 #1800 seconds = 30 minutes
                except:
                    print('Wallpaper upload failed')
                    next_call += 40 # if it bugs out, try again in a second
            
            #If wallpaper wasn't put up, then put up normal picture from link
            else:
                link, tag = self._choose_pic()
                pic = self._download_pics(link)
                
                #Tweepy won't upload things that are over 3072kb. 
                #loop runs until it finds a pic of suitable size.
                try:
                    while os.path.getsize(pic) > (3072 * 1000):
                        print('pic too big retrying')
                        self._delete_pic(pic)
                        link, tag= self._choose_pic() #choose a different link
                        pic = self._download_pics(link)
                
                    #Upload the pic, delete it, and set timer for 30 minutes
                    if tag == "None":
                        self.api.update_with_media(pic, status = '30 minutes, ba-BAM! A new anime pic! If you like this one, follow for more anime pics! \n')
                        
                    else:
                        self.api.update_with_media(pic, status = "Here's a pic of {}! If you like this one, follow for more anime pics! \n".format(tag))
                        
                    print('I uploaded a pic!')
                    self._delete_pic(pic)
                    next_call += 1200
                    
                    update_timer += 1
                    wallpaper_timer += 1
                
                except:
                    print('Something fishy is afoot')
                    self._delete_pic(pic)
                    next_call += 60
                
            time.sleep(next_call - time.time())#unless error from wallpaper, will sleep 30min
                

def main():
    testBot = Bot()
    testBot.mainloop()
    

    
if __name__ == '__main__':
    main()    
