import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import locale
import itchat
from apscheduler.schedulers.blocking import BlockingScheduler
import time
import city_dict
import yaml


class robot:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36",
    }


    def __init__(self):
        (self.girlfriend_list, self.alarm_hour, self.alarm_minute) = self.get_init_data()
        locale.setlocale(locale.LC_CTYPE, 'zh_CN.utf8')


    def get_init_data(self):
        # 打开雅玛配置文件
        with open('_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)


        alarm_timed = config.get('alarm_timed').strip()
        init_msg = f"每天定时发送时间: {alarm_timed}\n"


        girlfriend_list = []
        girlfriend_inifos = config.get('girlfriend_infos')
        for girlfriend in girlfriend_inifos:
            girlfriend.get('wechat_name').strip()
            city_name = girlfriend.get('city_name').strip()
            city_code = city_dict.city_dict.get(city_name)
            if not city_code:
                print('无法获取所在城市的信息')
                break
            girlfriend['city_code'] = city_code
            girlfriend_list.append(girlfriend)

            print_msg = f"女朋友的微信昵称：{girlfriend.get('wechat_name')}\n\t女友所在城市名称：{girlfriend.get('city_name')}\n\t" \
                f"在一起的第一天日期：{girlfriend.get('start_date')}\n\t最后一句为：{girlfriend.get('sweet_words')}\n"
            init_msg += print_msg


        print(u"*" * 50)
        print(init_msg)


        hour, minute = [int(x) for x in alarm_timed.split(':')]

        return (girlfriend_list, hour, minute)

    def is_online(self, auto_login=False):
        '''
        判断是否还在线,
        :param auto_login:True,如果掉线了则自动登录。
        :return: True ，还在线，False 不在线了
        '''

        def online():
            '''
            通过获取好友信息，判断用户是否还在线
            :return: True ，还在线，False 不在线了
            '''
            try:
                if itchat.search_friends():
                    return True
            except:
                return False
            return True

        if online():
            return True
        # 仅仅判断是否在线
        if not auto_login:
            return online()

        # 登陆，尝试 5 次
        for _ in range(5):
            # 命令行显示登录二维码
            itchat.auto_login(enableCmdQR=2)
            # itchat.auto_login()
            if online():
                print('登录成功')
                return True
        else:
            print('登录成功')
            return False


    def run(self):
        '''
        主运行入口
        :return:None
        '''
        # 自动登录
        if not self.is_online(auto_login=True):
            return
        for girlfriend in self.girlfriend_list:
            wechat_name = girlfriend.get('wechat_name')
            friends = itchat.search_friends(name=wechat_name)
            if not friends:
                print('昵称错误')
                return
            name_uuid = friends[0].get('UserName')
            girlfriend['name_uuid'] = name_uuid

        # 定时任务
        scheduler = BlockingScheduler()

        scheduler.add_job(self.start_today_info, 'cron', hour=self.alarm_hour, minute=self.alarm_minute)
        # 每隔1分钟发送一条数据用于测试。
        # scheduler.add_job(self.start_today_info, 'interval', seconds=60)
        scheduler.start()


    def start_today_info(self):
        '''
        每日定时开始处理。
        :return: None
        '''
        print("*" * 50)
        print('获取相关信息...')
        dictum_msg = self.get_dictum_info()

        for girlfriend in self.girlfriend_list:
            city_code = girlfriend.get('city_code')
            start_date = girlfriend.get('start_date')
            sweet_words = girlfriend.get('sweet_words')
            today_msg = self.get_weather_info(dictum_msg, city_code=city_code, start_date=start_date,
                                              sweet_words=sweet_words)
            name_uuid = girlfriend.get('name_uuid')
            wechat_name = girlfriend.get('wechat_name')
            print(f'给 {wechat_name} 发送的内容是:\n{today_msg}')
            if self.is_online(auto_login=True):
                itchat.send(today_msg, toUserName=name_uuid)
            # 防止信息发送过快。
            time.sleep(5)

        print('发送成功..\n')


    def get_dictum_info(self):
        '''
        获取格言信息（从『一个。one』获取信息 http://wufazhuce.com/）
        :return: str 一句格言或者短语
        '''
        print('获取格言信息..')
        user_url = 'http://wufazhuce.com/'
        resp = requests.get(user_url, headers=self.headers)
        soup_texts = BeautifulSoup(resp.text, 'lxml')
        # 『one -个』 中的每日一句
        every_msg = soup_texts.find_all('div', class_='fp-one-cita')[0].find('a').text
        return every_msg


    def get_weather_info(self, dictum_msg='', city_code='101270101', start_date='2018-05-20', sweet_words='来自最爱你的天才WHY'):
        '''
        获取天气信息。网址：https://www.sojson.com/blog/305.html
        :param dictum_msg: 发送给朋友的信息
        :param city_code: 城市对应编码
        :param start_date: 恋爱第一天日期
        :param sweet_words: 来自谁的留言
        :return: 需要发送的话。
        '''
        print('获取天气信息..')
        weather_url = f'http://t.weather.sojson.com/api/weather/city/{city_code}'
        resp = requests.get(url=weather_url)
        if resp.status_code == 200 and resp.json().get('status') == 200:
            weatherJson = resp.json()
            # 今日天气
            today_weather = weatherJson.get('data').get('forecast')[1]
            # 今日日期
            today_time = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
            # 今日天气注意事项
            notice = today_weather.get('notice')
            # 温度
            high = today_weather.get('high')
            high_c = high[high.find(' ') + 1:]
            low = today_weather.get('low')
            low_c = low[low.find(' ') + 1:]
            temperature = f"温度 : {low_c}/{high_c}"

            # 风
            fx = today_weather.get('fx')
            fl = today_weather.get('fl')
            wind = f"{fx} : {fl}"

            # 空气指数
            aqi = today_weather.get('aqi')
            aqi = f"空气 : {aqi}"

            # 在一起，一共多少天了
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            day_delta = (datetime.now() - start_datetime).days
            delta_msg = f"宝贝这是我们在一起的第 {day_delta} 天"

            today_msg = f"{today_time}\n到你中午该吃饭的时间了！记得好好吃饭！好好喝水！遵守交通规则！\n{delta_msg}！\n{notice}\n{temperature}\n{wind}\n{aqi}\n{dictum_msg}\n{sweet_words}\n"
            return today_msg


if __name__ == '__main__':

    robot().run()


