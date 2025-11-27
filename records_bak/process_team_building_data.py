import pandas as pd
import re

def process_team_building_data(file_path='team_building_record_20250331_ori.csv'):
    """
    处理团建记录CSV文件：
    1. 读取CSV文件
    2. 显示所有列名
    3. 删除所有'Unnamed'列
    4. 对特定列进行重命名
    5. 删除Player为'占位'的行
    6. 显示处理后的数据基本信息
    7. 返回处理后的DataFrame
    
    Args:
        file_path (str): CSV文件路径
        
    Returns:
        pandas.DataFrame: 处理后的数据框
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(file_path)
        
        # 显示原始数据信息
        print(f"原始数据形状（行 x 列）: {df.shape}")
        
        # 显示所有列名
        print("\n原始列名:")
        for col in df.columns:
            print(f"- {col}")
        
        # 找出包含'Unnamed'的列
        unnamed_cols = [col for col in df.columns if 'Unnamed' in col]
        
        if unnamed_cols:
            # 删除包含'Unnamed'的列
            df = df.drop(columns=unnamed_cols)
            print(f"\n已删除 {len(unnamed_cols)} 个Unnamed列: {unnamed_cols}")
        else:
            print("\n没有发现Unnamed列")
        
        # 对特定列进行重命名
        column_mapping = {
            '时间': 'Time',
            '税率': 'ServiceFee_Rate',
            '姓名': 'Player',
            '金额': 'Chips',
            '结算方式': 'WinOrLose',
            '计算值': 'Value',
            '税后': 'FinalChips'
        }
        
        # 仅重命名存在的列
        existing_cols = {}
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                existing_cols[old_name] = new_name
        
        # 执行重命名
        if existing_cols:
            df = df.rename(columns=existing_cols)
            print("\n已重命名以下列:")
            for old_name, new_name in existing_cols.items():
                print(f"- {old_name} => {new_name}")
        else:
            print("\n没有找到需要重命名的列")
            
        # 删除Player为'占位'的行
        if 'Player' in df.columns:
            initial_count = len(df)
            df = df[~df['Player'].isin(['占位','宏健','阳齐'])]
            removed_count = initial_count - len(df)
            if removed_count > 0:
                print(f"\n已删除 {removed_count} 行 Player='占位' 的数据")
            else:
                print("\n没有找到 Player='占位' 的行")
        elif '姓名' in df.columns:  # 如果Player列命名失败，尝试使用原始列名
            initial_count = len(df)
            df = df[~df['Player'].isin(['占位','宏健','阳齐'])]
            removed_count = initial_count - len(df)
            if removed_count > 0:
                print(f"\n已删除 {removed_count} 行 姓名='占位' 的数据")
            else:
                print("\n没有找到 姓名='占位' 的行")
        
        # 显示处理后的列名和数据信息
        print("\n处理后的列名:")
        for col in df.columns:
            print(f"- {col}")
        
        print(f"\n处理后数据形状（行 x 列）: {df.shape}")
        print("\n数据预览 (前5行):")
        print(df.head())
        
        # 数据类型信息
        print("\n数据类型:")
        print(df.dtypes)
        
        # 基本统计信息
        print("\n基本统计信息:")
        print(df.describe())
        
        return df
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{file_path}'。请检查文件路径是否正确。")
    except pd.errors.EmptyDataError:
        print(f"错误: 文件 '{file_path}' 是空的。")
    except pd.errors.ParserError:
        print(f"错误: 无法解析文件 '{file_path}'。文件格式可能不正确。")
        
        # 尝试使用不同的分隔符
        try:
            print("尝试使用自动检测分隔符...")
            df = pd.read_csv(file_path, sep=None, engine='python')
            print("成功读取文件！")
            
            # 继续处理列名和删除Unnamed列
            unnamed_cols = [col for col in df.columns if 'Unnamed' in col]
            if unnamed_cols:
                df = df.drop(columns=unnamed_cols)
                print(f"已删除 {len(unnamed_cols)} 个Unnamed列")
            
            # 对特定列进行重命名
            column_mapping = {
                '时间': 'Time',
                '税率': 'ServiceFee_Rate',
                '姓名': 'Player',
                '金额': 'Chips',
                '结算方式': 'WinOrLose',
                '计算值': 'Value',
                '税后': 'FinalChips'
            }
            
            # 仅重命名存在的列
            existing_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
            if existing_cols:
                df = df.rename(columns=existing_cols)
                print("\n已重命名列:")
                for old_name, new_name in existing_cols.items():
                    print(f"- {old_name} => {new_name}")
            
            # 删除Player为'占位'的行
            if 'Player' in df.columns:
                initial_count = len(df)
                df = df[~df['Player'].isin(['占位','宏健','阳齐'])]
                removed_count = initial_count - len(df)
                if removed_count > 0:
                    print(f"\n已删除 {removed_count} 行 Player='占位','宏健','阳齐'的数据")
            elif '姓名' in df.columns:
                initial_count = len(df)
                df = df[~df['姓名'].isin(['占位','宏健','阳齐'])]
                removed_count = initial_count - len(df)
                if removed_count > 0:
                    print(f"\n已删除 {removed_count} 行 姓名='占位','宏健','阳齐'的数据")
            
            return df
            
        except Exception as e:
            print(f"使用自动分隔符检测仍然失败: {e}")
            
    except Exception as e:
        print(f"读取文件时出现未知错误: {e}")
    
    return None

def calculate_player_statistics(df):
    """
    根据Player维度统计各项指标：
    1. WinChips: 每个Player的FinalChips累加和
    2. AttendCount: 每个Player的参与记录总次数(不去重)
    3. WinCount: 每个Player的FinalChips大于零的次数
    4. LoseCount: 每个Player的FinalChips小于零的次数
    5. PeaceCount: 每个Player的FinalChips等于零的次数
    6. WinningRate: 每个Player的胜率 (WinCount / AttendCount)
    7. Ranking: 按照WinChips进行排名
    
    Args:
        df (pandas.DataFrame): 处理后的数据框
        
    Returns:
        pandas.DataFrame: 包含所有统计指标的数据框，按WinChips排名
    """
    if df is None or 'Player' not in df.columns or 'FinalChips' not in df.columns:
        print("错误: 数据框为空或缺少必要的列(Player, FinalChips)")
        return None
    
    try:
        # 确保FinalChips是数值类型
        df['FinalChips'] = pd.to_numeric(df['FinalChips'], errors='coerce')
        
        # 创建一个新的DataFrame来存储统计结果
        stats = pd.DataFrame()
        
        # 1. 计算每个Player的WinChips (FinalChips累加和)
        stats['WinChips'] = df.groupby('Player')['FinalChips'].sum()
        
        # 2. 计算每个Player的参与次数 (总次数，不去重)
        stats['AttendCount'] = df['Player'].value_counts()
        
        # 3. 计算每个Player的胜利次数 (FinalChips > 0)
        stats['WinCount'] = df[df['FinalChips'] > 0].groupby('Player').size()
        # 处理没有胜利的情况
        stats['WinCount'] = stats['WinCount'].fillna(0).astype(int)
        
        # 4. 计算每个Player的失败次数 (FinalChips < 0)
        stats['LoseCount'] = df[df['FinalChips'] < 0].groupby('Player').size()
        # 处理没有失败的情况
        stats['LoseCount'] = stats['LoseCount'].fillna(0).astype(int)
        
        # 5. 计算每个Player的平局次数 (FinalChips = 0)
        stats['PeaceCount'] = df[df['FinalChips'] == 0].groupby('Player').size()
        # 处理没有平局的情况
        stats['PeaceCount'] = stats['PeaceCount'].fillna(0).astype(int)
        
        # 6. 计算每个Player的胜率 (WinCount / AttendCount)
        stats['WinningRate'] = stats['WinCount'] / stats['AttendCount']
        # 格式化为百分比
        stats['WinningRate'] = stats['WinningRate'].apply(lambda x: f"{x:.2%}")
        
        # 7. 按照WinChips排序并添加排名
        stats = stats.sort_values('WinChips', ascending=False)
        stats['Ranking'] = range(1, len(stats) + 1)
        
        # 重新排列列顺序
        stats = stats[['Ranking', 'WinChips', 'AttendCount', 'WinCount', 'LoseCount', 'PeaceCount', 'WinningRate']]
        
        # 重置索引，将Player列移到前面
        stats = stats.reset_index()
        
        return stats
        
    except Exception as e:
        print(f"计算统计数据时出错: {e}")
        return None

def convert_chinese_date_format(df):
    """
    将DataFrame中的中文日期格式'yyyy年MM月dd日'转换为标准格式'yyyy-MM-dd'
    
    Args:
        df (pandas.DataFrame): 包含Time列的DataFrame
    
    Returns:
        pandas.DataFrame: 日期格式已转换的DataFrame
    """
    if df is None or 'Time' not in df.columns:
        print("警告: 无法转换日期格式，数据为空或未找到Time列")
        return df
    
    def convert_date(date_str):
        if not isinstance(date_str, str):
            return date_str
            
        # 已经是标准格式
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
            
        # 转换中文格式
        match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if match:
            year = match.group(1)
            month = match.group(2).zfill(2)  # 确保两位数
            day = match.group(3).zfill(2)    # 确保两位数
            return f"{year}-{month}-{day}"
            
        return date_str
    
    # 转换Time列的日期格式
    df['Time'] = df['Time'].apply(convert_date)
    print("\n已将日期格式从'yyyy年MM月dd日'转换为'yyyy-MM-dd'")
    
    return df

def save_processed_data(df, output_path='team_building_record.csv'):
    """
    保存处理后的数据到CSV文件
    
    Args:
        df (pandas.DataFrame): 处理后的数据框
        output_path (str): 输出文件路径
    """
    if df is not None:
        # 转换日期格式
        df = convert_chinese_date_format(df)
        df.to_csv(output_path, index=False)
        print(f"\n已将处理后的数据保存为: {output_path}")
    else:
        print("没有数据可保存")

def save_player_statistics(stats, output_path='player_statistics.csv'):
    """
    保存玩家统计数据到CSV文件
    
    Args:
        stats (pandas.DataFrame): 玩家统计数据框
        output_path (str): 输出文件路径
    """
    if stats is not None:
        stats.to_csv(output_path, index=False)
        print(f"\n已将玩家统计数据保存为: {output_path}")
    else:
        print("没有统计数据可保存")

if __name__ == "__main__":
    # 处理数据
    processed_df = process_team_building_data()
    
    # 保存处理后的数据
    save_processed_data(processed_df)
    
    # 计算并显示玩家统计数据
    if processed_df is not None:
        player_stats = calculate_player_statistics(processed_df)
        if player_stats is not None:
            print("\n玩家统计数据:")
            print(player_stats)
            
            # 保存玩家统计数据
            save_player_statistics(player_stats) 